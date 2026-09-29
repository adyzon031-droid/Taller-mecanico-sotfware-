"""Reglas de negocio del registro de clientes."""
from datetime import date
import re


class ClienteError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def validar(datos):
    if not isinstance(datos, dict):
        raise ClienteError("El cuerpo debe ser un objeto JSON")
    required = ("nombre_completo", "edad", "fecha_nacimiento", "telefono_personal", "telefono_trabajo", "email", "calle", "colonia", "municipio", "estado", "codigo_postal")
    faltan = [campo for campo in required if datos.get(campo) in (None, "")]
    if faltan:
        raise ClienteError("Campos requeridos: " + ", ".join(faltan))
    email_re = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    phone_re = r"^\+?[0-9 ()-]{7,20}$"
    if not re.fullmatch(email_re, str(datos["email"])) or (datos.get("email_trabajo") and not re.fullmatch(email_re, str(datos["email_trabajo"]))):
        raise ClienteError("Formato de correo inválido")
    if any(not re.fullmatch(phone_re, str(datos[key])) for key in ("telefono_personal", "telefono_trabajo")):
        raise ClienteError("Formato de teléfono inválido")
    if not re.fullmatch(r"\d{5}", str(datos["codigo_postal"])):
        raise ClienteError("El código postal debe contener cinco dígitos")
    try:
        nacimiento = date.fromisoformat(str(datos["fecha_nacimiento"]))
        edad = int(datos["edad"])
    except (ValueError, TypeError):
        raise ClienteError("Fecha de nacimiento o edad inválida")
    hoy = date.today()
    edad_calculada = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    if nacimiento > hoy or edad < 0 or edad != edad_calculada:
        raise ClienteError("La edad no coincide con la fecha de nacimiento")
    normalizados = {key: (str(value).strip() if value is not None else None) for key, value in datos.items()}
    normalizados.setdefault("contacto_alterno", None)
    normalizados.setdefault("email_trabajo", None)
    return normalizados


class ClienteFacade:
    def __init__(self, repository):
        self.repository = repository

    def crear(self, datos, sesion, foto_contexto=None, foto_ruta=None):
        datos = validar(datos)
        datos.update(taller_id=sesion["taller_id"], creado_por=sesion["usuario_id"], foto_ruta=foto_ruta)
        if self.repository.duplicado(sesion["taller_id"], datos):
            raise ClienteError("Ya existe un cliente con esos datos", 409)
        return self.repository.crear(datos, foto_contexto)

    def listar(self, sesion, filtros):
        return self.repository.listar(sesion["taller_id"], filtros)

    def obtener(self, sesion, cliente_id):
        return self.repository.obtener(sesion["taller_id"], cliente_id)

    def actualizar(self, sesion, cliente_id, datos):
        datos = validar(datos)
        if self.repository.duplicado(sesion["taller_id"], datos, cliente_id):
            raise ClienteError("Ya existe un cliente con esos datos", 409)
        return self.repository.actualizar(sesion["taller_id"], cliente_id, datos)
