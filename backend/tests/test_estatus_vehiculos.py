from datetime import date
import pytest

from estatus_facade import EstatusFacade, StatusError
from estatus_repository import EstatusRepository
from vehiculo_facade import VehiculoFacade, VehicleError


def test_estatus_normaliza_y_valida_descripcion():
    facade=EstatusFacade(None)
    assert facade.validate({'valor':'  Otro   estado ','descripcion':' Texto descriptivo '})==('otro estado','Texto descriptivo')
    with pytest.raises(StatusError) as error:facade.validate({'valor':'1!','descripcion':'x'})
    assert error.value.status==422 and {'valor','descripcion'}<=set(error.value.errors)


def test_estatus_lista_blanca_y_tamano_de_pagina():
    from pagination import parse_page
    assert parse_page({'page_size':'100'},EstatusRepository.SORT,'valor').page_size==50
    with pytest.raises(ValueError):parse_page({'sort':'nombre;drop'},EstatusRepository.SORT,'valor')


def vehicle(**changes):
    data={'cliente_id':1,'placa':'abc-123','marca':'Nissan','anio':2020,'fecha_ingreso':date.today().isoformat()}
    data.update(changes);return data


def test_vehicle_normalizes_plate_and_omitted_optionals():
    clean=VehiculoFacade.validate(vehicle())
    assert clean['placa']=='ABC123' and clean['modelo'] is None and clean['numero_serie'] is None


@pytest.mark.parametrize('data,field',[
    (vehicle(placa='bad'), 'placa'),(vehicle(placa=''), 'placa'),(vehicle(marca=''), 'marca'),
    (vehicle(anio=1899),'anio'),(vehicle(anio=date.today().year+2),'anio'),
    (vehicle(fecha_ingreso='2999-01-01'),'fecha_ingreso'),(vehicle(fecha_ingreso='2020-01-01'),'fecha_ingreso'),
    (vehicle(numero_serie='I'*17),'numero_serie'),(vehicle(kilometraje=2_000_001),'kilometraje'),
    (vehicle(version='x'*41),'version'),
])
def test_vehicle_rejects_invalid_fields(data,field):
    with pytest.raises(VehicleError) as error:VehiculoFacade.validate(data)
    assert error.value.status==422 and field in error.value.errors


def test_vehicle_warns_on_old_date_and_bad_vin_check_digit():
    old=(date.today().replace(day=1)).isoformat()
    clean=VehiculoFacade.validate(vehicle(fecha_ingreso=old,numero_serie='1M8GDM9AXKP042788',anio=2019),today=date.today())
    assert clean['_warnings']


def test_estatus_options_read_and_admin_write(monkeypatch):
    import app as module
    class Repo:
        def options(self):return [{'valor':'activo'}]
        def list(self,*args,**kwargs):return {'items':[],'total':0,'page':1,'page_size':10,'total_pages':0}
        def get(self,*args):return {'id':1,'valor':'activo'}
    monkeypatch.setattr(module,'estatus_repository',Repo())
    client=module.app.test_client()
    with client.session_transaction() as s:s['usuario']={'usuario_id':1,'taller_id':1,'rol':'recepcionista'}
    assert client.get('/api/estatus/opciones').status_code==200
    assert client.post('/api/estatus',json={'valor':'nuevo','descripcion':'estado nuevo'}).status_code==403


def vehicle_activation(**changes):
    data=vehicle(modelo='Versa',version='Advance',numero_serie='1M8GDM9AXKP042788',kilometraje=0)
    data.update(changes)
    return data


@pytest.mark.parametrize('field,value',[
    ('modelo',''),('version',''),('numero_serie',''),('kilometraje',None),
])
def test_activation_requires_the_complete_vehicle_file(field,value):
    data=vehicle_activation(**{field:value})
    with pytest.raises(VehicleError) as error:
        VehiculoFacade.validar_activacion(data)
    assert error.value.status==422 and field in error.value.errors


def test_activation_accepts_zero_mileage_and_reuses_normalization():
    clean=VehiculoFacade.validar_activacion(vehicle_activation(placa=' abc-123 '))
    assert clean['placa']=='ABC123' and clean['kilometraje']==0


@pytest.mark.parametrize('body,field',[
    ({'confirmado':True,'motivo':'  Revisión programada  '},None),
    ({'confirmado':False,'motivo':'Revisión programada'},'confirmado'),
    ({'confirmado':True,'motivo':'x'},'motivo'),
])
def test_deactivation_requires_confirmation_and_reason(body,field):
    if field is None:
        assert VehiculoFacade.validar_desactivacion(body)=={'motivo':'Revisión programada'}
        return
    with pytest.raises(VehicleError) as error:
        VehiculoFacade.validar_desactivacion(body)
    assert error.value.status==422 and field in error.value.errors


def test_vehicle_transition_routes_apply_status_and_scope_errors(monkeypatch):
    import app as module

    class Repo:
        def activate(self,user,vehicle_id,data):
            if vehicle_id==404:return None
            if vehicle_id==409:raise VehicleError('Solo se puede activar un vehículo con estatus inactivo.',409)
            return {'vehiculo':{'id':vehicle_id,'estatus':'activo'},'warnings':[]}
        def deactivate(self,user,vehicle_id,motivo):
            if vehicle_id==404:return None
            if vehicle_id==409:raise VehicleError('Solo se puede desactivar un vehículo con estatus activo.',409)
            return {'id':vehicle_id,'estatus':'inactivo'}

    monkeypatch.setattr(module,'vehiculo_repository',Repo())
    client=module.app.test_client()
    payload=vehicle_activation()
    with client.session_transaction() as s:s['usuario']={'usuario_id':1,'taller_id':1,'rol':'administrador'}
    assert client.patch('/api/vehiculos/9/activar',json=payload).status_code==200
    assert client.patch('/api/vehiculos/404/activar',json=payload).status_code==404
    assert client.patch('/api/vehiculos/409/activar',json=payload).status_code==409
    assert client.patch('/api/vehiculos/9/desactivar',json={'confirmado':True,'motivo':'Mantenimiento detenido'}).status_code==200
    assert client.patch('/api/vehiculos/404/desactivar',json={'confirmado':True,'motivo':'Mantenimiento detenido'}).status_code==404
    assert client.patch('/api/vehiculos/409/desactivar',json={'confirmado':True,'motivo':'Mantenimiento detenido'}).status_code==409
    assert client.patch('/api/vehiculos/9/desactivar',json={'confirmado':False,'motivo':'Mantenimiento detenido'}).status_code==422


def test_vehicle_transition_routes_reject_insufficient_role():
    import app as module
    client=module.app.test_client()
    with client.session_transaction() as s:s['usuario']={'usuario_id':1,'taller_id':1,'rol':'mecanico'}
    assert client.patch('/api/vehiculos/9/activar',json=vehicle_activation()).status_code==403
    assert client.patch('/api/vehiculos/9/desactivar',json={'confirmado':True,'motivo':'Mantenimiento detenido'}).status_code==403


def test_deactivation_writes_audit_before_commit(monkeypatch):
    import vehiculo_repository as module
    events=[]
    row={'id':9,'cliente_id':2,'taller_id':1,'placa':'ABC123','placa_vigente':'ABC123','marca_id':1,'modelo_id':2,'marca_texto':'Nissan','modelo_texto':'Versa','anio':2020,'version':'Advance','numero_serie':'1M8GDM9AXKP042788','serie_vigente':'1M8GDM9AXKP042788','kilometraje':0,'fecha_ingreso':'2026-01-01','estatus_id':1,'estatus':'activo','deleted_at':None}

    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*_):return False
        def execute(self,sql,args=()):
            events.append(('audit' if 'INSERT INTO auditoria' in sql else 'update' if sql.startswith('UPDATE vehiculos') else 'query',args))
            self.last_sql=sql
        def fetchone(self):
            if 'SELECT v.*,e.valor estatus' in self.last_sql:return dict(row)
            if 'SELECT id FROM estatus' in self.last_sql:return {'id':2}
            return None

    class Connection:
        def cursor(self):return Cursor()
        def commit(self):events.append(('commit',()))
        def rollback(self):events.append(('rollback',()))
        def close(self):events.append(('close',()))

    repo=module.VehiculoRepository()
    monkeypatch.setattr(module,'connect',lambda:Connection())
    monkeypatch.setattr(repo,'get',lambda user,record_id:{'id':record_id,'estatus':'inactivo'})
    assert repo.deactivate({'usuario_id':7,'taller_id':1},9,'Mantenimiento detenido')['estatus']=='inactivo'
    names=[event[0] for event in events]
    assert names.index('update')<names.index('audit')<names.index('commit')

