from datetime import date

import phonenumbers
import pytest

from cliente_facade import ClienteError, validar
from identidad_mexico import validar_curp
from ubicacion_facade import UbicacionFacade


def valid_client():
    return {
        "nombres":"Alicia", "apellido_paterno":"Pérez", "apellido_materno":"Gómez",
        "curp":"GODE561231HDFRRNA0", "fecha_nacimiento":"1956-12-31", "edad":date.today().year-1956-((date.today().month,date.today().day)<(12,31)),
        "celular":"5512345678", "telefono_personal":"5512345678", "telefono_trabajo":"5587654321",
        "email": "a@example.test", "calle": "Calle 1", "colonia": "Centro",
        "contacto":{"nombre":"Ana Pérez","telefono_personal":"5522223333","telefono_personal_prefijo":"52","telefono_personal_pais":"MX","email":"ana@example.test"},
        "municipio": "Tula de Allende", "estado": "Hidalgo", "codigo_postal": "42800",
    }


@pytest.mark.parametrize("prefix,region,number", [
    ("52", "MX", str(phonenumbers.example_number_for_type("MX", phonenumbers.PhoneNumberType.MOBILE).national_number)),
    ("1", "US", str(phonenumbers.example_number_for_type("US", phonenumbers.PhoneNumberType.MOBILE).national_number)),
])
def test_validates_mexican_and_foreign_phone(prefix, region, number):
    data = valid_client()
    data.update(celular=number, celular_prefijo=prefix, celular_pais=region, telefono_personal=number)
    assert validar(data)["celular"] == number


@pytest.mark.parametrize("number", ["551234567", "55123456789", "55ABC45678"])
def test_rejects_invalid_mexican_phone(number):
    data = valid_client()
    data["celular"] = number
    with pytest.raises(ClienteError) as exc:
        validar(data)
    assert "celular" in exc.value.errors


class FakeLocationRepository:
    def __init__(self, loaded=True):
        self.loaded = loaded

    def catalogo_cargado(self):
        return self.loaded

    def cp(self, cp):
        if cp != "42800":
            return []
        return [
            {"cp": cp, "estado": "Hidalgo", "municipio": "Tula de Allende", "colonia": "Centro", "tipo_asentamiento": "Colonia"},
            {"cp": cp, "estado": "Hidalgo", "municipio": "Tula de Allende", "colonia": "Unidad 2", "tipo_asentamiento": "Colonia"},
            {"cp": cp, "estado": "Hidalgo", "municipio": "Tlahuelilpan", "colonia": "Centro", "tipo_asentamiento": "Colonia"},
        ]

    def estados(self):
        return ["Hidalgo"]

    def municipios(self, estado):
        return ["Tula de Allende"]

    def colonias(self, estado, municipio, query):
        return [{"colonia": "Centro", "cp": "42800"}]

    def buscar(self, estado, municipio, colonia):
        return ["42800", "42801"]

    def direccion_valida(self, estado, municipio, colonia, cp):
        return (estado, municipio, colonia, cp) == ("Hidalgo", "Tula de Allende", "Centro", "42800")


def test_location_catalog_endpoints_facade_contract():
    service = UbicacionFacade(FakeLocationRepository())
    result = service.cp("42800")
    assert result["estados"] == ["Hidalgo"]
    assert result["municipios"] == ["Tlahuelilpan", "Tula de Allende"]
    assert len(result["colonias"]) == 3
    assert service.buscar("Hidalgo", "Tula de Allende", "Centro") == ["42800", "42801"]


def test_location_missing_or_empty_catalog_errors():
    with pytest.raises(ClienteError) as missing:
        UbicacionFacade(FakeLocationRepository()).cp("99999")
    assert missing.value.status == 404
    with pytest.raises(ClienteError) as unavailable:
        UbicacionFacade(FakeLocationRepository(False)).estados()
    assert unavailable.value.status == 503


def test_address_validation_uses_loaded_catalog():
    data = valid_client()
    assert validar(data, ubicacion_repository=FakeLocationRepository())["codigo_postal"] == "42800"
    data["codigo_postal"] = "99999"
    with pytest.raises(ClienteError) as exc:
        validar(data, ubicacion_repository=FakeLocationRepository())
    assert exc.value.status == 422
    assert "codigo_postal" in exc.value.errors
