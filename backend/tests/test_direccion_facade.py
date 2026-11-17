import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cliente_facade import ClienteError
from ubicacion_facade import UbicacionFacade


ROWS = [
    {"cp": "10000", "estado": "Hidalgo", "municipio": "Municipio A", "colonia": "Centro", "tipo_asentamiento": "Colonia"},
    {"cp": "10000", "estado": "Hidalgo", "municipio": "Municipio A", "colonia": "Alto", "tipo_asentamiento": "Colonia"},
    {"cp": "20000", "estado": "Hidalgo", "municipio": "Municipio A", "colonia": "Centro", "tipo_asentamiento": "Colonia"},
    {"cp": "30000", "estado": "Estado B", "municipio": "Municipio B", "colonia": "Centro", "tipo_asentamiento": "Colonia"},
]


class FakeUbicacionRepository:
    def catalogo_cargado(self):
        return True

    def cp(self, cp):
        return [row for row in ROWS if row["cp"] == cp]

    def direccion_valida(self, estado, municipio, colonia, cp):
        return any((r["estado"], r["municipio"], r["colonia"], r["cp"]) == (estado, municipio, colonia, cp) for r in ROWS)

    def buscar(self, estado, municipio, colonia):
        return sorted({r["cp"] for r in ROWS if (r["estado"], r["municipio"], r["colonia"]) == (estado, municipio, colonia)})


@pytest.fixture
def service():
    return UbicacionFacade(FakeUbicacionRepository())


def test_cp_with_single_colony(service):
    result = service.cp("30000")
    assert result["estados"] == ["Estado B"]
    assert result["municipios"] == ["Municipio B"]
    assert result["colonias"][0]["colonia"] == "Centro"


def test_cp_with_multiple_colonies(service):
    assert {x["colonia"] for x in service.cp("10000")["colonias"]} == {"Centro", "Alto"}


def test_cp_with_multiple_municipalities(service):
    assert service.cp("30000")["municipios"] == ["Municipio B"]
    # The multi-municipality branch is checked with multiple records for one CP.
    service.repository.cp = lambda cp: ROWS[:1] + [{**ROWS[3], "cp": cp}]
    assert service.cp("40000")["municipios"] == ["Municipio A", "Municipio B"]


def test_cp_not_found_returns_404(service):
    with pytest.raises(ClienteError) as error:
        service.cp("99999")
    assert error.value.status == 404
    assert str(error.value) == "Código postal no encontrado"


def test_colony_with_multiple_postal_codes(service):
    assert service.buscar("Hidalgo", "Municipio A", "Centro") == ["10000", "20000"]


def test_incoherent_combination_is_rejected_and_manual_is_allowed(service):
    assert service.direccion_valida("Hidalgo", "Municipio A", "Centro", "20000")
    assert not service.direccion_valida("Estado B", "Municipio B", "Alto", "30000")
    assert service.direccion_valida("Estado B", "Municipio B", "Colonia no catalogada", "30000", manual=True)


def test_incoherent_client_address_returns_http_422(monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import app as module
    from test_clientes import cliente_valido

    class InvalidLocation:
        def direccion_valida(self, *args, **kwargs):
            return False

    monkeypatch.setattr(module.facade, "ubicacion_service", InvalidLocation())
    client = module.app.test_client()
    with client.session_transaction() as session:
        session["usuario"] = {"usuario_id": 5, "taller_id": 3, "rol": "recepcionista"}
    response = client.post("/api/clientes", json=cliente_valido())
    assert response.status_code == 422
    assert "codigo_postal" in response.json["errors"]


def test_backend_colony_rows_keep_cp_for_cp_selection(service):
    rows = service.cp("10000")["colonias"]
    # Duplicate names are deduplicated by the frontend projection; service keeps full source rows.
    assert len(rows) == 2
    assert all("cp" not in row for row in rows)


def test_frontend_colony_options_deduplicate_names():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js no está disponible")
    root = Path(__file__).resolve().parents[2]
    script = """
      import { opcionesColoniasUnicas } from './frontend/direccion/direccionFacade.js';
      const rows = opcionesColoniasUnicas([
        {colonia:'Alto',cp:'42807'}, {colonia:'alto',cp:'42808'}, {colonia:'Centro',cp:'42801'}
      ]);
      process.stdout.write(JSON.stringify(rows.map(row => row.colonia)));
    """
    result = subprocess.run(
        [node, "--experimental-default-type=module", "--input-type=module", "-e", script],
        cwd=root, check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout) == ["Alto", "Centro"]


def test_cors_allows_only_explicit_origins(monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import app as module
    monkeypatch.setenv("CORS_ORIGINS", "http://127.0.0.1:34871, https://torque.example")
    client = module.app.test_client()
    allowed = client.get("/api/ubicacion/estados", headers={"Origin": "http://127.0.0.1:34871"})
    denied = client.get("/api/ubicacion/estados", headers={"Origin": "http://127.0.0.1:34872"})
    assert allowed.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:34871"
    assert allowed.headers.get("Access-Control-Allow-Credentials") == "true"
    assert denied.headers.get("Access-Control-Allow-Origin") is None
