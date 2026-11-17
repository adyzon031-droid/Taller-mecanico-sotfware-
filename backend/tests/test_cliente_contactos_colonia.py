import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cliente_facade import ClienteError, ClienteFacade, validar
from cliente_repository import ClienteRepository
from ubicacion_repository import UbicacionRepository
from test_clientes import cliente_valido


@pytest.mark.parametrize("field", ["celular", "email"])
def test_cliente_requiere_telefono_personal_y_correo(field):
    data = cliente_valido()
    data[field] = ""
    with pytest.raises(ClienteError) as exc:
        validar(data)
    assert field in exc.value.errors


@pytest.mark.parametrize("field", ["nombre", "telefono_personal", "email"])
def test_contacto_requiere_nombre_telefono_y_correo(field):
    data = cliente_valido()
    data["contacto"][field] = ""
    with pytest.raises(ClienteError) as exc:
        validar(data)
    assert f"contacto.{field}" in exc.value.errors


def test_api_devuelve_422_con_mapa_de_errores_para_contacto_requerido():
    from app import app as flask_app
    client = flask_app.test_client()
    with client.session_transaction() as session:
        session["usuario"] = {"usuario_id": 5, "taller_id": 3, "rol": "recepcionista"}
    response = client.post("/api/clientes", json={"celular":"", "email":"", "contacto":{}})
    assert response.status_code == 422
    assert isinstance(response.json.get("errors"), dict)
    assert "contacto.nombre" in response.json["errors"]
    assert "contacto.telefono_personal" in response.json["errors"]
    assert "contacto.email" in response.json["errors"]


def test_campos_de_trabajo_omitidos_son_validos():
    data = cliente_valido()
    assert validar(data)["contacto"]["telefono_trabajo"] is None
    assert validar(data)["contacto"]["email_trabajo"] == ""


def test_correo_laboral_contacto_debe_ser_distinto():
    data = cliente_valido()
    data["contacto"]["email_trabajo"] = data["contacto"]["email"].upper()
    with pytest.raises(ClienteError) as exc:
        validar(data)
    assert "contacto.email_trabajo" in exc.value.errors


@pytest.mark.parametrize("kind", ["telefono", "correo"])
def test_contacto_no_repite_telefono_ni_correo_del_cliente(kind):
    data = cliente_valido()
    if kind == "telefono":
        data["contacto"]["telefono_personal"] = data["celular"]
    else:
        data["contacto"]["email"] = data["email"].upper()
    with pytest.raises(ClienteError) as exc:
        validar(data)
    assert "contacto." in next(iter(exc.value.errors))


def test_mismo_contacto_se_puede_asociar_a_clientes_distintos():
    class Repository:
        def __init__(self): self.created = 0
        def duplicado(self, workshop_id, values, exclude_id=None): return False
        def crear(self, values, photo_context=None): self.created += 1; return self.created

    repo = Repository()
    facade = ClienteFacade(repo)
    user = {"rol": "recepcionista", "taller_id": 3, "usuario_id": 4}
    data = cliente_valido()
    assert facade.crear(data, user) == 1
    data["email"] = "otra@example.com"
    data["celular"] = "5511112222"
    data["telefono_personal"] = data["celular"]
    assert facade.crear(data, user) == 2


@pytest.mark.parametrize("field", ["email", "celular"])
def test_cliente_duplicado_por_correo_o_telefono_responde_409(field):
    class Repository:
        def duplicado(self, workshop_id, values, exclude_id=None): return True

    with pytest.raises(ClienteError) as exc:
        ClienteFacade(Repository()).crear(cliente_valido(), {"rol": "recepcionista", "taller_id": 3, "usuario_id": 4})
    assert exc.value.status == 409


@pytest.mark.parametrize("field,expected_sql", [
    ("email", "email=%s"),
    ("celular", "(telefono_personal_prefijo=%s AND telefono_personal=%s)"),
])
def test_repository_busca_duplicados_solo_en_telefono_o_correo_del_cliente(field, expected_sql, monkeypatch):
    calls = []
    monkeypatch.setattr(ClienteRepository, "_run", staticmethod(lambda sql, args=(), fetch="all": calls.append((sql,args)) or {"id": 1}))
    data = validar(cliente_valido())
    if field == "email": data["celular"] = data["telefono_personal"] = None
    else: data["email"] = None
    assert ClienteRepository().duplicado(2, data) is True
    assert expected_sql in calls[0][0]
    assert "cliente_contactos" not in calls[0][0]


def test_colonia_del_catalogo_y_cp_no_coincidente():
    class Location:
        def catalogo_cargado(self): return True
        def direccion_valida(self, state, municipality, colony, cp): return cp == "50000"

    assert validar(cliente_valido(), ubicacion_repository=Location())["colonia"] == "Centro"
    with pytest.raises(ClienteError) as exc:
        validar({**cliente_valido(), "codigo_postal": "50001"}, ubicacion_repository=Location())
    assert "codigo_postal" in exc.value.errors


def test_colonia_manual_omite_catalogo_y_se_guarda_con_bandera():
    class Location:
        def catalogo_cargado(self): return True
        def direccion_valida(self, *args): raise AssertionError("No debe consultar el catálogo para captura manual")

    data = {**cliente_valido(), "colonia": "Privada El Encino", "colonia_manual": True}
    result = validar(data, ubicacion_repository=Location())
    assert result["colonia_manual"] is True


def test_catalogo_entrega_lista_completa_ordenada_y_filtro_parcial(monkeypatch):
    calls=[]
    repo=UbicacionRepository()
    monkeypatch.setattr(repo,"_many",lambda sql,args:calls.append((sql,args)) or [])
    repo.colonias("Hidalgo","Tula de Allende","")
    assert "ORDER BY colonia,cp LIMIT 5000" in calls[-1][0]
    assert calls[-1][1]==("Hidalgo","Tula de Allende","%%")
    repo.colonias("Hidalgo","Tula de Allende","Centro")
    assert calls[-1][1]==("Hidalgo","Tula de Allende","%Centro%")


def test_falla_guardado_contacto_revierte_alta_cliente(monkeypatch):
    class Cursor:
        lastrowid = 123
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, *_): pass
        def fetchone(self): return {"id": 1}

    class Connection:
        committed = False
        rolled_back = False
        closed = False
        def cursor(self): return Cursor()
        def commit(self): self.committed = True
        def rollback(self): self.rolled_back = True
        def close(self): self.closed = True

    connection = Connection()
    monkeypatch.setattr("cliente_repository.connect", lambda: connection)
    monkeypatch.setattr(ClienteRepository, "_save_contact", staticmethod(lambda *_: (_ for _ in ()).throw(RuntimeError("contact failed"))))
    values = validar(cliente_valido())
    values.update(taller_id=1, creado_por=1)
    with pytest.raises(RuntimeError):
        ClienteRepository().crear(values)
    assert connection.rolled_back and not connection.committed and connection.closed
