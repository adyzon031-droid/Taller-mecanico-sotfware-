"""Validación del catálogo de estados."""
import re


class StatusError(ValueError):
    def __init__(self, message, status=422, errors=None):
        super().__init__(message)
        self.status = status
        self.errors = errors or {}


SYSTEM = {"activo", "en espera", "inactivo", "suspendido", "eliminado"}


class EstatusFacade:
    def __init__(self, repository):
        self.repository = repository

    def validate(self, data):
        if not isinstance(data, dict):
            raise StatusError("El cuerpo debe ser un objeto JSON.", errors={"_global": "El cuerpo debe ser un objeto JSON."})
        value = " ".join(str(data.get("valor", "")).lower().split())
        description = " ".join(str(data.get("descripcion", "")).split())
        errors = {}
        if not 3 <= len(value) <= 30 or not re.fullmatch(r"[a-záéíóúüñ]+(?: [a-záéíóúüñ]+)*", value):
            errors["valor"] = "Usa de 3 a 30 letras y espacios."
        if not 5 <= len(description) <= 255:
            errors["descripcion"] = "Usa de 5 a 255 caracteres."
        if errors:
            raise StatusError("Revisa los campos indicados.", errors=errors)
        return value, description
