"""Validación y normalización del catálogo de marcas y modelos."""
import re
import unicodedata


class CatalogError(ValueError):
    def __init__(self, message, status=422, errors=None):
        super().__init__(message)
        self.status = status
        self.errors = errors or {}


ACRONYMS = {"BMW", "GMC", "RAM", "SEAT"}


def normalizar_nombre(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    result = []
    for word in value.split(" "):
        parts = word.split("-")
        result.append("-".join(p.upper() if p.upper() in ACRONYMS else p[:1].upper() + p[1:].lower() for p in parts))
    return " ".join(result)


def comparar_nombre(value):
    decomposed = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


class VehicleCatalogFacade:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def validar_nombre(value, field, maximum):
        name = normalizar_nombre(value)
        if not name:
            raise CatalogError("Revisa los datos del catálogo.", errors={field: "Este campo es obligatorio."})
        if len(name) > maximum:
            raise CatalogError("Revisa los datos del catálogo.", errors={field: f"Máximo {maximum} caracteres."})
        if not re.fullmatch(r"[\wÀ-ÿ][\wÀ-ÿ .&'’()/+-]*", name, re.UNICODE):
            raise CatalogError("Revisa los datos del catálogo.", errors={field: "Usa letras, números y separadores habituales."})
        return name

    def marca(self, data):
        if not isinstance(data, dict):
            raise CatalogError("El cuerpo debe ser un objeto JSON.", errors={"_global": "El cuerpo debe ser un objeto JSON."})
        return self.validar_nombre(data.get("nombre"), "nombre", 60)

    def modelo(self, data):
        if not isinstance(data, dict):
            raise CatalogError("El cuerpo debe ser un objeto JSON.", errors={"_global": "El cuerpo debe ser un objeto JSON."})
        name = self.validar_nombre(data.get("nombre"), "nombre", 80)
        try:
            brand_id = int(data.get("marca_id"))
            if brand_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise CatalogError("Selecciona una marca válida.", errors={"marca_id": "Selecciona una marca válida."})
        return brand_id, name

    @staticmethod
    def pagination(args):
        try:
            page = int(args.get("page", 1))
            page_size = int(args.get("page_size", 10))
        except (TypeError, ValueError):
            raise CatalogError("Paginación inválida.", errors={"page": "Usa números enteros."})
        if page < 1 or not 1 <= page_size <= 100:
            raise CatalogError("Paginación inválida.", errors={"page_size": "Debe estar entre 1 y 100."})
        sort = args.get("sort", "nombre")
        direction = args.get("direction", "asc").lower()
        if sort not in {"nombre", "estatus", "created_at"} or direction not in {"asc", "desc"}:
            raise CatalogError("Orden inválido.", errors={"sort": "Orden o dirección no permitidos."})
        return page, page_size, sort, direction

    def resolve_pending(self, data):
        if not isinstance(data, dict):
            raise CatalogError("El cuerpo debe ser un objeto JSON.")
        brand_id = data.get("marca_id")
        brand_name = data.get("marca")
        model_name = data.get("modelo")
        if brand_id:
            try:
                brand_id = int(brand_id)
            except (TypeError, ValueError):
                raise CatalogError("Selecciona una marca válida.", errors={"marca_id": "Selecciona una marca válida."})
        else:
            brand_name = self.validar_nombre(brand_name, "marca", 60)
        if model_name not in (None, ""):
            model_name = self.validar_nombre(model_name, "modelo", 80)
        elif not brand_id and not brand_name:
            raise CatalogError("La marca es obligatoria.", errors={"marca": "La marca es obligatoria."})
        return self.repository.resolve_pending(brand_id, brand_name, model_name)
