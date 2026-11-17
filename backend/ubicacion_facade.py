"""Reglas de disponibilidad para países y ubicaciones."""
from cliente_facade import ClienteError


class UbicacionFacade:
    def __init__(self, repository):
        self.repository = repository

    def paises(self):
        rows = self.repository.paises()
        if not rows:
            raise ClienteError("Catálogo de países no disponible.", 503)
        return rows

    def _catalogo(self):
        if not self.repository.catalogo_cargado():
            raise ClienteError("Catálogo de códigos postales no cargado", 503)

    def cp(self, cp):
        self._catalogo()
        rows = self.repository.cp(cp)
        if not rows:
            raise ClienteError("Código postal no encontrado", 404)
        return {
            "cp": cp,
            "estados": sorted({row["estado"] for row in rows}),
            "municipios": sorted({row["municipio"] for row in rows}),
            "colonias": [{"colonia": row["colonia"], "municipio": row["municipio"], "estado": row["estado"], "tipo_asentamiento": row["tipo_asentamiento"]} for row in rows],
        }

    def estados(self):
        self._catalogo()
        return self.repository.estados()

    def municipios(self, estado):
        self._catalogo()
        return self.repository.municipios(estado)

    def colonias(self, estado, municipio, q):
        self._catalogo()
        return self.repository.colonias(estado, municipio, q)

    def buscar(self, estado, municipio, colonia):
        self._catalogo()
        return self.repository.buscar(estado, municipio, colonia)

    def catalogo_cargado(self):
        return self.repository.catalogo_cargado()

    def direccion_valida(self, estado, municipio, colonia, cp, manual=False):
        if manual or not self.repository.catalogo_cargado():
            return True
        return self.repository.direccion_valida(estado, municipio, colonia, cp)
