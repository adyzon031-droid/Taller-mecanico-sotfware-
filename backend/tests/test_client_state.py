import pytest

from cliente_facade import ClienteError, ClienteFacade


@pytest.mark.parametrize('status,method', [('suspendido', 'suspender'), ('activo', 'reactivar')])
def test_estado_cliente_administrador_devuelve_200(monkeypatch, status, method):
    import app as app_module

    class FakeFacade:
        def __init__(self):
            self.called = None

        def suspender(self, user, client_id, user_id, reason):
            self.called = ('suspendido', client_id, user_id, reason)
            return True

        def reactivar(self, user, client_id, user_id):
            self.called = ('activo', client_id, user_id, None)
            return True

    fake = FakeFacade()
    monkeypatch.setattr(app_module, 'facade', fake)
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session['usuario'] = {'usuario_id': 7, 'taller_id': 2, 'rol': 'administrador'}
    response = client.patch('/api/clientes/81/estado', json={'estado': status, 'motivo': 'prueba'})
    assert response.status_code == 200
    assert response.json['mensaje'] == 'Estado actualizado'
    assert fake.called == (status, 81, 7, 'prueba' if method == 'suspender' else None)


def test_recepcionista_no_puede_suspender_cliente():
    from app import app as flask_app

    client = flask_app.test_client()
    with client.session_transaction() as session:
        session['usuario'] = {'usuario_id': 8, 'taller_id': 2, 'rol': 'recepcionista'}
    response = client.patch('/api/clientes/81/estado', json={'estado': 'suspendido'})
    assert response.status_code == 403


def test_cliente_fuera_del_taller_devuelve_404(monkeypatch):
    import app as app_module

    class FakeFacade:
        def suspender(self, user, client_id, user_id, reason):
            return False

    monkeypatch.setattr(app_module, 'facade', FakeFacade())
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session['usuario'] = {'usuario_id': 7, 'taller_id': 2, 'rol': 'administrador'}
    response = client.patch('/api/clientes/987654321/estado', json={'estado': 'suspendido'})
    assert response.status_code == 404
    assert response.json['error'] == 'Cliente no encontrado'


def test_cliente_suspendido_se_reactiva_por_la_misma_ruta(monkeypatch):
    import app as app_module

    class FakeFacade:
        def reactivar(self, user, client_id, user_id):
            assert (client_id, user_id) == (81, 7)
            return True

    monkeypatch.setattr(app_module, 'facade', FakeFacade())
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session['usuario'] = {'usuario_id': 7, 'taller_id': 2, 'rol': 'administrador'}
    response = client.patch('/api/clientes/81/estado', json={'estado': 'activo'})
    assert response.status_code == 200


def test_no_se_puede_editar_cliente_suspendido():
    class FakeRepository:
        def obtener(self, user, client_id):
            return {'estado_cliente': 'suspendido', 'taller_id': 2}

    facade = ClienteFacade(FakeRepository())
    with pytest.raises(ClienteError) as error:
        facade.actualizar({'rol': 'administrador', 'taller_id': 2}, 81, {})
    assert error.value.status == 409


def test_edicion_legada_permite_apellido_y_curp_ausentes():
    from test_clientes import cliente_valido

    class FakeRepository:
        def obtener(self, user, client_id):
            return {'estado_cliente': 'activo', 'datos_por_completar': 1, 'taller_id': 2}

        def duplicado(self, workshop_id, values, client_id):
            return False

        def taller_de_empresa(self, workshop_id, session_taller_id):
            return True

        def actualizar(self, user, client_id, values, photo_context=None):
            self.saved = values
            return True

    repository = FakeRepository()
    facade = ClienteFacade(repository)
    data = cliente_valido()
    data['nombres'] = 'mCDONALD'
    data['apellido_paterno'] = ''
    data['apellido_materno'] = ''
    data['curp'] = ''
    data['taller_id'] = 2
    assert facade.actualizar({'rol': 'administrador', 'taller_id': 2}, 81, data) is True
    assert repository.saved['apellido_paterno'] == ''
    assert repository.saved['curp'] == ''
    assert repository.saved['nombre_completo'] == 'mCDONALD'
    assert repository.saved['datos_por_completar'] == 1
