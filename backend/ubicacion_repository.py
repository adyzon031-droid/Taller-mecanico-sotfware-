"""Consultas parametrizadas para el catálogo SEPOMEX local y países."""
import json
from pathlib import Path

from db import connect


class UbicacionRepository:
    def __init__(self):
        self.paises_file = Path(__file__).resolve().parent / "data" / "paises.json"

    def paises(self):
        try:
            return json.loads(self.paises_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    def catalogo_cargado(self):
        return bool(self._one("SELECT COUNT(*) AS n FROM codigos_postales")["n"])

    def cp(self, cp):
        return self._many(
            "SELECT DISTINCT cp,estado,municipio,colonia,tipo_asentamiento FROM codigos_postales "
            "WHERE cp=%s ORDER BY estado,municipio,colonia", (cp,))

    def estados(self):
        return [row["estado"] for row in self._many(
            "SELECT DISTINCT estado FROM codigos_postales ORDER BY estado", ())]

    def municipios(self, estado):
        return [row["municipio"] for row in self._many(
            "SELECT DISTINCT municipio FROM codigos_postales WHERE estado=%s ORDER BY municipio", (estado,))]

    def colonias(self, estado, municipio, query):
        pattern = f"%{query}%"
        return self._many(
            "SELECT DISTINCT colonia,cp FROM codigos_postales WHERE estado=%s AND municipio=%s "
            "AND colonia LIKE %s ORDER BY colonia,cp LIMIT 5000", (estado, municipio, pattern))

    def buscar(self, estado, municipio, colonia):
        return [row["cp"] for row in self._many(
            "SELECT DISTINCT cp FROM codigos_postales WHERE estado=%s AND municipio=%s AND colonia=%s ORDER BY cp",
            (estado, municipio, colonia))]

    def direccion_valida(self, estado, municipio, colonia, cp):
        return self._one(
            "SELECT 1 AS valido FROM codigos_postales WHERE estado=%s AND municipio=%s AND colonia=%s AND cp=%s LIMIT 1",
            (estado, municipio, colonia, cp)) is not None

    @staticmethod
    def _one(sql, args=()):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, args)
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def _many(sql, args=()):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, args)
                return cursor.fetchall()
        finally:
            connection.close()
