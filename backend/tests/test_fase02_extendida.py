from io import BytesIO
from werkzeug.datastructures import FileStorage
import pytest
from pymysql.err import IntegrityError

from cliente_facade import ClienteError, ClienteFacade
from identidad_mexico import normalizar_palabras, validar_curp, validar_rfc_persona_fisica


def client_data():
    return {
        "nombres":"Ernesto","apellido_paterno":"Gómez","apellido_materno":"Díaz",
        "fecha_nacimiento":"1956-12-31","edad":69,"curp":"GODE561231HDFRRNA0",
        "rfc":"GODE561231ABC","celular":"2221234567","celular_prefijo":"52","celular_pais":"MX",
        "contacto":{"nombre":"Ana Pérez","telefono_personal":"5512345679","telefono_personal_prefijo":"52","telefono_personal_pais":"MX","email":"contacto@example.test"},
        "telefono_fijo":"","telefono_trabajo":"","email":"persona@example.test",
        "calle":"Calle Uno","colonia":"Centro","municipio":"Tula de Allende",
        "estado":"Hidalgo","codigo_postal":"42800",
    }


@pytest.mark.parametrize("value,birth,expected",[
    ("GODE561231HDFRRNA0","1956-12-31",True),
    ("GODE561332HDFRRNA0","1956-13-32",False),
    ("GODE561231HDFRRNA1","1956-12-31",False),
    ("GODE561231HDFRRNA0","1957-12-31",False),
    ("not-a-curp","1956-12-31",False),
])
def test_curp_validation_structure_date_checksum_and_birth(value,birth,expected):
    assert validar_curp(value,birth) is expected


@pytest.mark.parametrize("value,expected",[
    ("GODE561231ABC",True),("GODE561332ABC",False),("ABC561231AB",False),("ABC561231ABC",False),
])
def test_rfc_persona_fisica_structure_and_date(value,expected):
    assert validar_rfc_persona_fisica(value) is expected


def test_normalization_case_email_and_phone():
    from cliente_facade import validar
    data=client_data();data.update(nombres="  ANA   MARÍA ",apellido_paterno="DE LA CRUZ",estado="hidalgo",email=" A@EXAMPLE.TEST ",celular="(222) 123-4567")
    normalized=validar(data)
    assert normalized["nombres"]=="Ana María"
    assert normalized["apellido_paterno"]=="de la Cruz"
    assert normalized["estado"]=="Hidalgo"
    assert normalized["email"]=="a@example.test"
    assert normalized["celular"]=="2221234567"


@pytest.mark.parametrize("field",["curp","rfc","email","celular","nombre_completo"])
def test_duplicate_field_is_conflict_409(field):
    class Repo:
        def duplicado(self,workshop,values,exclude=None):return True
    data=client_data()
    with pytest.raises(ClienteError) as exc:
        ClienteFacade(Repo()).crear(data,{"taller_id":1,"usuario_id":1,"rol":"recepcionista"})
    assert exc.value.status==409


@pytest.mark.parametrize("filename,mime,body",[
    ("workshop.jpg","image/jpeg",b"\xff\xd8\xff"+b"x"*(15*1024*1024)),
    ("wrong.png","image/png",b"\xff\xd8\xff"),
])
def test_workshop_photo_rejects_size_and_fake_extension(filename,mime,body):
    from app import _validar_foto
    fs=FileStorage(stream=BytesIO(body),filename=filename,content_type=mime)
    with pytest.raises(ClienteError) as exc:_validar_foto(fs)
    assert exc.value.status==422 and "foto" in exc.value.errors


def test_duplicate_workshop_integrity_is_409(monkeypatch):
    import app as module
    class Fake:
        def crear(self,user,data):raise IntegrityError(1062,"duplicate")
    monkeypatch.setattr(module,"taller_facade",Fake())
    client=module.app.test_client()
    with client.session_transaction() as sess:sess["usuario"]={"usuario_id":7,"taller_id":1,"rol":"administrador"}
    assert client.post("/api/talleres",json={}).status_code==409


def test_receptionist_is_scoped_and_cannot_suspend_or_reactivate(monkeypatch):
    import app as module
    client=module.app.test_client()
    with client.session_transaction() as sess:sess["usuario"]={"usuario_id":7,"taller_id":999999,"rol":"recepcionista"}
    assert client.get("/api/clientes/1").status_code==404
    assert client.patch("/api/clientes/1/estado",json={"estado":"suspendido"}).status_code==403
    assert client.patch("/api/clientes/1/estado",json={"estado":"activo"}).status_code==403


def test_administrator_can_suspend_and_reactivate_in_facade(monkeypatch):
    import app as module
    class Fake:
        calls=[]
        def suspender(self,user,cid,uid,reason):self.calls.append(("suspend",cid,uid,reason));return True
        def reactivar(self,user,cid,uid):self.calls.append(("activate",cid,uid));return True
    fake=Fake();monkeypatch.setattr(module,"facade",fake)
    client=module.app.test_client()
    with client.session_transaction() as sess:sess["usuario"]={"usuario_id":7,"taller_id":1,"rol":"administrador"}
    assert client.patch("/api/clientes/3/estado",json={"estado":"suspendido","motivo":"revisión"}).status_code==200
    assert client.patch("/api/clientes/3/estado",json={"estado":"activo"}).status_code==200
    assert [call[0] for call in fake.calls]==["suspend","activate"]


def test_sort_whitelist_and_server_pagination():
    from app import app
    client=app.test_client()
    with client.session_transaction() as sess:sess["usuario"]={"usuario_id":1,"taller_id":1,"rol":"administrador"}
    assert client.get("/api/clientes?sort=created_at%20DESC").status_code==400
    asc=client.get("/api/clientes?page=1&page_size=10&sort=nombre&direction=asc")
    desc=client.get("/api/clientes?page=1&page_size=10&sort=nombre&direction=desc")
    assert asc.status_code==desc.status_code==200
    names=[row["nombre_completo"] for row in asc.json["clientes"]]
    assert names==sorted(names,key=str.casefold)
    assert client.get("/api/clientes?page=1&page_size=25&sort=fecha&direction=desc").json["page_size"]==25
    oversized=client.get("/api/clientes?page=1&page_size=51")
    assert oversized.status_code==400
    assert oversized.json=={"error":"El tamaño máximo permitido es 50.","errors":{"page_size":"El tamaño máximo permitido es 50."}}


def test_taller_scope_and_receptionist_cannot_mutate_workshops():
    from app import app
    client=app.test_client()
    with client.session_transaction() as sess:sess["usuario"]={"usuario_id":4,"taller_id":1,"rol":"recepcionista"}
    response=client.get("/api/talleres")
    assert response.status_code==200 and len(response.json["talleres"])==1
    assert client.post("/api/talleres",json={}).status_code==403
    assert client.put("/api/talleres/1",json={}).status_code==403
    assert client.patch("/api/talleres/1/estado",json={"activo":False}).status_code==403
