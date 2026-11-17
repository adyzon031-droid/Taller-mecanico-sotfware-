import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from app import app, vehiculo_catalogo_facade
from vehiculo_catalogo_facade import CatalogError, VehicleCatalogFacade
from vehiculo_catalogo_repository import VehicleCatalogRepository


class FakeCatalog:
    def options(self, q=''):
        return [{'id': 1, 'nombre': 'Nissan', 'estatus': 'activo', 'pendiente': False}]
    def model_options(self, brand_id, q=''):
        return [{'id': 2, 'marca_id': brand_id, 'nombre': 'Versa', 'estatus': 'activo'}]
    def search(self, q, brand_id=None):
        return [{'tipo': 'combinacion', 'etiqueta': 'Nissan · Versa'}][:10]
    def list(self, *args, **kwargs):
        return {'items': [], 'total': 0, 'page': 1, 'page_size': 10, 'pages': 0}


def as_user(client, role='administrador'):
    with client.session_transaction() as session:
        session['usuario'] = {'usuario_id': 1, 'taller_id': 1, 'rol': role}


def test_catalog_routes_are_admin_only(monkeypatch):
    monkeypatch.setattr('app.vehiculo_catalogo_repository', FakeCatalog())
    client = app.test_client()
    as_user(client, 'recepcionista')
    assert client.get('/api/marcas').status_code == 403
    assert client.post('/api/marcas', json={'nombre': 'Prueba'}).status_code == 403
    assert client.get('/api/modelos').status_code == 403
    assert client.patch('/api/modelos/1/desactivar').status_code == 403


def test_selectors_search_and_search_limit(monkeypatch):
    monkeypatch.setattr('app.vehiculo_catalogo_repository', FakeCatalog())
    client = app.test_client(); as_user(client, 'recepcionista')
    assert client.get('/api/marcas/opciones?q=VER').json['marcas'][0]['nombre'] == 'Nissan'
    assert client.get('/api/marcas/1/modelos/opciones').json['modelos'][0]['nombre'] == 'Versa'
    assert len(client.get('/api/catalogo-vehiculos/buscar?q=%25_').json['resultados']) <= 10
    assert client.get('/api/catalogo-vehiculos/buscar?q=').json['resultados'] == []


def test_catalog_validation_and_no_delete_endpoint():
    client = app.test_client(); as_user(client)
    response = client.post('/api/marcas', json={'nombre': '  '})
    assert response.status_code == 422
    assert client.delete('/api/marcas/1').status_code == 405
    assert client.delete('/api/modelos/1').status_code == 405


def test_name_normalization_and_limits():
    assert VehicleCatalogFacade(None).marca({'nombre': '  mErCeDeS-bEnZ  '}) == 'Mercedes-Benz'
    assert VehicleCatalogFacade(None).marca({'nombre': 'bmw'}) == 'BMW'
    with pytest.raises(CatalogError) as error:
        VehicleCatalogFacade(None).modelo({'marca_id': 'no', 'nombre': 'Versa'})
    assert error.value.status == 422 and 'marca_id' in error.value.errors


def test_prefix_query_escapes_special_characters():
    assert VehicleCatalogRepository._safe_prefix('a%_b\\c') == 'a\\%\\_b\\\\c'
    assert VehicleCatalogRepository._safe_prefix('Ver') == 'Ver'


def test_catalog_database_seed_and_accent_insensitive_prefix():
    repo = VehicleCatalogRepository()
    brands = repo.options('NIS')
    assert any(row['nombre'] == 'Nissan' for row in brands)
    assert len(repo.search('VER')) <= 10
    assert any(row.get('modelo') == 'Versa' for row in repo.search('Vér'))
    assert len(repo.search('%_')) <= 10
