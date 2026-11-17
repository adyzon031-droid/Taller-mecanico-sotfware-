from datetime import date
from io import BytesIO

import pytest

from cliente_facade import ClienteError, validar
from identidad_mexico import validar_curp


def curp_for(birth):
    c=list("GODE561231HDFRRNA0")
    c[4:10]=list(birth[2:4]+birth[5:7]+birth[8:10])
    c[16]='A'
    alphabet="0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
    c[17]=str((10-sum(alphabet.index(ch)*(18-i) for i,ch in enumerate(c[:17]))%10)%10)
    return ''.join(c)


def cliente_valido():
    return {
        "nombres":"Ernesto", "apellido_paterno":"Gómez", "apellido_materno":"Díaz",
        "nombre_completo":"Ernesto Gómez Díaz", "curp":"GODE561231HDFRRNA0",
        "rfc":"GODE561231ABC", "fecha_nacimiento":"1956-12-31",
        "contacto":{"nombre":"Ana Pérez","telefono_personal":"5522223333","telefono_personal_prefijo":"52","telefono_personal_pais":"MX","email":"ana.contacto@example.com"},
        "celular":"5512345678", "telefono_fijo":"", "telefono_trabajo":"5587654321",
        "email":"JOSE@example.com", "email_trabajo":"contacto@example.com",
        "calle":"Av. Reforma 10", "numero_interior":"",
        "colonia":"Centro", "municipio":"Toluca", "estado":"Estado de México", "codigo_postal":"50000",
    }


@pytest.mark.parametrize("field,value", [
    ("nombres", "Ernesto"), ("celular", "5512345678"),
    ("telefono_trabajo", "5587654321"), ("email", "persona@example.com"),
    ("fecha_nacimiento", "1980-01-01"), ("estado", "Jalisco"),
    ("codigo_postal", "01000"), ("municipio", "San Pedro"), ("colonia", "Centro"),
    ("calle", "Calle 1"), ("contacto_alterno", "Ana Pérez"),
])
def test_campo_acepta_formato_valido(field, value):
    data=cliente_valido(); data[field]=value
    if field == "fecha_nacimiento":
        age=date.today().year-1980-((date.today().month,date.today().day)<(1,1)); data['edad']=age
        data['curp']=curp_for("1980-01-01")
    assert validar(data)[field] == (value.lower() if field == "email" else value)


@pytest.mark.parametrize("field,value,error", [
    ("nombres", "Jose1", "nombres"),
    ("celular", "55A2345678", "celular"),
    ("celular", "123456789", "celular"),
    ("telefono_trabajo", "12345678901", "telefono_trabajo"),
    ("email", "no-es-correo", "email"), ("estado", "Estado inventado", "estado"),
    ("codigo_postal", "1234A", "codigo_postal"),
    ("fecha_nacimiento", "2099-01-01", "fecha_nacimiento"),
    ("contacto_alterno", "Ana3 López", "contacto_alterno"),
])
def test_campo_rechaza_formato_invalido(field,value,error):
    data=cliente_valido(); data[field]=value
    if field == "fecha_nacimiento": data['edad']=72
    with pytest.raises(ClienteError) as exc: validar(data)
    assert error in exc.value.errors


def test_normaliza_textos_y_email():
    data=cliente_valido(); data['nombres']='  josé   maria  '; data['apellido_paterno']='de la cruz'; data['email']=' JOSE@EXAMPLE.COM '
    result=validar(data)
    assert result['nombre_completo']=='José Maria de la Cruz Díaz'
    assert result['email']=='jose@example.com'


def test_edad_incoherente():
    data=cliente_valido(); data['edad']=12
    with pytest.raises(ClienteError) as exc: validar(data)
    assert 'edad' in exc.value.errors


def test_correo_trabajo_debe_ser_distinto():
    data=cliente_valido(); data['email_trabajo']=data['email'].upper()
    with pytest.raises(ClienteError) as exc: validar(data)
    assert 'email_trabajo' in exc.value.errors


def test_foto_mayor_15_mib_rechazada(monkeypatch):
    from app import app as flask_app
    client=flask_app.test_client()
    with client.session_transaction() as session:
        session['usuario']={'usuario_id':1,'taller_id':1,'rol':'recepcionista'}
    response=client.post('/api/clientes',data={
        'cliente':'{}','foto':(BytesIO(b'\xff\xd8\xff'+b'x'*(15*1024*1024)), 'large.jpg','image/jpeg')
    },content_type='multipart/form-data')
    assert response.status_code == 422
    assert 'foto' in response.json['errors']


def test_recepcionista_no_puede_eliminar():
    from app import app as flask_app
    client=flask_app.test_client()
    with client.session_transaction() as session:
        session['usuario']={'usuario_id':1,'taller_id':1,'rol':'recepcionista'}
    assert client.delete('/api/clientes/12').status_code == 403


def test_cliente_de_otro_taller_devuelve_404(monkeypatch):
    import app as app_module
    class FakeFacade:
        def obtener(self,session,client_id):
            assert session['taller_id']==2
            return None
    monkeypatch.setattr(app_module,'facade',FakeFacade())
    client=app_module.app.test_client()
    with client.session_transaction() as session:
        session['usuario']={'usuario_id':9,'taller_id':2,'rol':'administrador'}
    assert client.get('/api/clientes/12').status_code == 404


def test_actualizar_conserva_foto_si_no_se_envia():
    from cliente_facade import ClienteFacade
    class Repository:
        def obtener(self, user, client_id):
            return {'id':client_id,'foto_ruta':'storage/clientes/existente.webp','taller_id':3,'estado_cliente':'activo'}
        def duplicado(self, workshop_id, data, excluir_id=None):
            assert excluir_id == 7
            return False
        def actualizar(self, user, client_id, data, foto_contexto=None):
            assert foto_contexto is None
            assert data['foto_ruta']=='storage/clientes/existente.webp'
            return True
    facade=ClienteFacade(Repository())
    assert facade.actualizar({'taller_id':3,'usuario_id':5,'rol':'recepcionista'},7,cliente_valido()) is True


def test_duplicado_facade_responde_409():
    from cliente_facade import ClienteFacade
    class Repository:
        def taller_de_empresa(self, target, current): return {'id':target}
        def duplicado(self, workshop_id, values, excluir_id=None): return True
    with pytest.raises(ClienteError) as exc:
        ClienteFacade(Repository()).crear(cliente_valido(),{'taller_id':4,'usuario_id':1,'rol':'recepcionista'})
    assert exc.value.status==409
