"""Validación y reglas de negocio del módulo de clientes."""
from datetime import date
import re


class ClienteError(ValueError):
    def __init__(self, message, status=422, errors=None):
        super().__init__(message)
        self.status = status
        self.errors = errors or {}


ESTADOS_MEXICO = (
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
    "Chiapas", "Chihuahua", "Ciudad de México", "Coahuila", "Colima",
    "Durango", "Estado de México", "Guanajuato", "Guerrero", "Hidalgo",
    "Jalisco", "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca",
    "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa",
    "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán",
    "Zacatecas",
)
_ESTADOS = {value.casefold(): value for value in ESTADOS_MEXICO}
_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)+$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

_LONGITUDES = {
    "nombre_completo": 180, "contacto_alterno": 180,
    "email": 190, "email_trabajo": 190,
    "calle": 180, "colonia": 120, "municipio": 120, "estado": 120,
}
_OBLIGATORIOS = (
    "nombre_completo", "fecha_nacimiento", "telefono_personal",
    "telefono_trabajo", "email", "calle", "colonia", "municipio",
    "estado", "codigo_postal",
)


def normalizar_texto(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def edad_desde_fecha(nacimiento, hoy=None):
    hoy = hoy or date.today()
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


def validar(datos, hoy=None):
    """Normaliza/valida el cuerpo y devuelve errores asociados a cada campo."""
    if not isinstance(datos, dict):
        raise ClienteError("El cuerpo debe ser un objeto JSON", errors={"_global": "El cuerpo debe ser un objeto JSON."})

    limpio = {key: normalizar_texto(value) if value is not None else "" for key, value in datos.items()}
    errores = {}
    for campo in _OBLIGATORIOS:
        if not limpio.get(campo):
            errores[campo] = "Este campo es obligatorio."

    for campo in ("nombre_completo", "contacto_alterno"):
        valor = limpio.get(campo, "")
        if valor and not _NOMBRE.fullmatch(valor):
            errores[campo] = "Escribe al menos dos palabras con letras, espacios, apóstrofo o guion."

    for campo in ("telefono_personal", "telefono_trabajo"):
        valor = limpio.get(campo, "")
        if valor and not re.fullmatch(r"\d{10}", valor):
            errores[campo] = "Ingresa 10 dígitos."

    for campo in ("email", "email_trabajo"):
        valor = limpio.get(campo, "")
        if valor:
            valor = valor.lower()
            limpio[campo] = valor
            if len(valor) > 190 or not _EMAIL.fullmatch(valor):
                errores[campo] = "Escribe un correo válido de máximo 190 caracteres."
    if limpio.get("email_trabajo") and limpio.get("email_trabajo") == limpio.get("email"):
        errores["email_trabajo"] = "Debe ser distinto al correo personal."

    fecha_txt = limpio.get("fecha_nacimiento", "")
    nacimiento = None
    if fecha_txt:
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha_txt):
                raise ValueError
            nacimiento = date.fromisoformat(fecha_txt)
        except ValueError:
            errores["fecha_nacimiento"] = "Ingresa una fecha real."
    if nacimiento:
        edad = edad_desde_fecha(nacimiento, hoy)
        if nacimiento > (hoy or date.today()):
            errores["fecha_nacimiento"] = "La fecha no puede ser futura."
        elif edad > 120:
            errores["fecha_nacimiento"] = "La fecha no puede superar 120 años."
        try:
            recibida = int(limpio.get("edad", ""))
        except (ValueError, TypeError):
            recibida = None
        if recibida != edad:
            errores["edad"] = "La edad no coincide con la fecha de nacimiento."
        limpio["edad"] = edad
    elif limpio.get("edad"):
        errores.setdefault("edad", "La edad se calcula con la fecha de nacimiento.")

    cp = limpio.get("codigo_postal", "")
    if cp and not re.fullmatch(r"\d{5}", cp):
        errores["codigo_postal"] = "Usa cinco dígitos."

    estado = limpio.get("estado", "")
    if estado:
        canonico = _ESTADOS.get(estado.casefold())
        if canonico is None:
            errores["estado"] = "Selecciona un estado de México."
        else:
            limpio["estado"] = canonico

    for campo, maximo in _LONGITUDES.items():
        if len(limpio.get(campo, "")) > maximo:
            errores[campo] = f"Máximo {maximo} caracteres."

    if errores:
        raise ClienteError("Revisa los campos indicados.", errors=errores)

    limpio["contacto_alterno"] = limpio.get("contacto_alterno") or None
    limpio["email_trabajo"] = limpio.get("email_trabajo") or None
    return limpio


class ClienteFacade:
    def __init__(self, repository):
        self.repository = repository

    def crear(self, datos, sesion, foto_contexto=None, foto_ruta=None):
        valores = validar(datos)
        valores.update(taller_id=sesion["taller_id"], creado_por=sesion["usuario_id"], foto_ruta=foto_ruta)
        if self.repository.duplicado(sesion["taller_id"], valores):
            raise ClienteError("Ya existe un cliente con esos datos.", 409)
        return self.repository.crear(valores, foto_contexto)

    def listar(self, sesion, filtros, page=1, per_page=10):
        return self.repository.listar(sesion["taller_id"], filtros, page, per_page)

    def obtener(self, sesion, cliente_id):
        return self.repository.obtener(sesion["taller_id"], cliente_id)

    def actualizar(self, sesion, cliente_id, datos, foto_contexto=None, foto_ruta=None):
        actual = self.repository.obtener(sesion["taller_id"], cliente_id)
        if not actual:
            return False
        valores = validar(datos)
        valores.update(
            taller_id=sesion["taller_id"],
            foto_ruta=foto_ruta if foto_ruta is not None else actual.get("foto_ruta"),
        )
        if self.repository.duplicado(sesion["taller_id"], valores, excluir_id=cliente_id):
            raise ClienteError("Ya existe un cliente con esos datos.", 409)
        return self.repository.actualizar(sesion["taller_id"], cliente_id, valores, foto_contexto)

    def eliminar(self, sesion, cliente_id):
        return self.repository.eliminar(sesion["taller_id"], cliente_id)
