import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from app import app, _employee_payload
from empleado_facade import EmpleadoFacade


@pytest.mark.parametrize("role", ["recepcionista", "mecanico"])
@pytest.mark.parametrize("method,path", [
    ("get", "/api/empleados"), ("post", "/api/empleados"),
    ("get", "/api/empleados/1"), ("put", "/api/empleados/1"),
    ("post", "/api/empleados/1/foto"), ("patch", "/api/empleados/1/baja"),
    ("patch", "/api/empleados/1/reactivar"), ("get", "/api/empleados/talleres"),
    ("get", "/api/empleados/verificar-duplicado?campo=email&valor=x%40example.test"),
    ("get", "/api/empleados/1/foto"),
])
def test_non_admin_roles_receive_403_for_employee_endpoints(role, method, path):
    client = app.test_client()
    with client.session_transaction() as session:
        session["usuario"] = {"usuario_id": 1, "taller_id": 1, "rol": role}
    response = getattr(client, method)(path, json={})
    assert response.status_code == 403


def test_payload_never_returns_password_hash():
    assert "password_hash" not in _employee_payload({"id": 1, "nombre": "Test", "password_hash": "secret-hash"})


def test_employee_validation_reports_missing_role_and_bad_identity():
    data, errors = EmpleadoFacade(None).validar({
        "nombres": "  ana   maria ", "apellido_paterno": "de la cruz",
        "email": "AN@example.test", "telefono_personal": "1234567890",
        "rol": "", "taller_id": 1, "curp": "INVALID", "rfc": "BAD",
    })
    assert errors["rol"] == "Selecciona un rol permitido."
    assert errors["curp"] and errors["rfc"]
    assert data["nombres"] == "Ana Maria"
