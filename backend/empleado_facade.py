"""Validación de negocio para empleados; las consultas permanecen en repository."""
import re
from datetime import date
from identidad_mexico import normalizar_palabras, validar_curp, validar_rfc_persona_fisica
import phonenumbers

ROLES={"administrador","recepcionista","mecanico"}
EMAIL=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
FIELDS=("nombres","apellido_paterno","apellido_materno","curp","rfc","fecha_nacimiento","telefono_personal","telefono_personal_prefijo","telefono_personal_pais","email","telefono_trabajo","telefono_trabajo_prefijo","telefono_trabajo_pais","email_trabajo","calle","numero_interior","codigo_postal","estado","municipio","colonia","colonia_manual","contacto_emergencia_nombre","contacto_emergencia_parentesco","contacto_emergencia_telefono","contacto_emergencia_prefijo","contacto_emergencia_pais","puesto","fecha_ingreso")

def _date(v):
    try:return date.fromisoformat(str(v)[:10]) if v else None
    except (ValueError,TypeError):return None

class EmpleadoFacade:
    def __init__(self,repository):self.repository=repository
    def validar(self,raw,creating=True):
        data={k:raw.get(k) for k in FIELDS}
        errors={}
        for key in ("nombres","apellido_paterno","puesto","estado","municipio","colonia","calle","contacto_emergencia_nombre","contacto_emergencia_parentesco"):
            if data.get(key) is not None:data[key]=normalizar_palabras(data[key]) or None
        for key in ("curp","rfc"):
            if data.get(key):data[key]=str(data[key]).strip().upper()
        for key in ("email","email_trabajo"):
            if data.get(key):data[key]=str(data[key]).strip().lower()
        for key in ("telefono_personal","telefono_trabajo","contacto_emergencia_telefono"):
            if raw.get(key) is not None:data[key]=re.sub(r"\D", "", str(raw.get(key) or "")) or None
        for key in FIELDS:
            if isinstance(data[key],str):data[key]=data[key].strip() or None
        data["email"]=str(raw.get("email","")).strip().lower()
        data["nombre"]=" ".join(filter(None,(data.get("nombres"),data.get("apellido_paterno"),data.get("apellido_materno"))))
        data["rol"]=str(raw.get("rol","")).strip().lower()
        try:data["taller_id"]=int(raw.get("taller_id"))
        except (ValueError,TypeError):data["taller_id"]=0
        if (creating or data.get("nombres")) and not data.get("nombres"):errors["nombres"]="Ingresa el nombre."
        if (creating or data.get("apellido_paterno")) and not data.get("apellido_paterno"):errors["apellido_paterno"]="Ingresa el apellido paterno."
        if not data["email"] or not EMAIL.fullmatch(data["email"]):errors["email"]="Ingresa un correo válido."
        if (creating or data.get("telefono_personal")) and (not data.get("telefono_personal") or not str(data["telefono_personal"]).isdigit()):errors["telefono_personal"]="Ingresa el teléfono personal en dígitos."
        for key in ("telefono_personal","telefono_trabajo","contacto_emergencia_telefono"):
            number=str(data.get(key) or "")
            if not number:
                continue
            country=str(raw.get(key+"_pais") or ("MX" if key=="telefono_personal" else "" )).upper()
            prefix=str(raw.get(key+"_prefijo") or ("52" if country=="MX" else ""))
            try:
                if not country or not prefix.isdigit() or phonenumbers.country_code_for_region(country)!=int(prefix):raise ValueError
                parsed=phonenumbers.parse("+"+prefix+number,country)
                if not phonenumbers.is_valid_number_for_region(parsed,country) or (prefix=="52" and len(number)!=10):raise ValueError
                data[key+"_pais"]=country;data[key+"_prefijo"]=prefix
            except (ValueError,phonenumbers.NumberParseException):errors[key]="Ingresa un teléfono válido para el país seleccionado."
        if data["rol"] not in ROLES:errors["rol"]="Selecciona un rol permitido."
        if not data["taller_id"]:errors["taller_id"]="Selecciona un taller."
        birth=_date(data.get("fecha_nacimiento"))
        if creating and not birth:errors["fecha_nacimiento"]="Ingresa la fecha de nacimiento."
        if data.get("fecha_nacimiento") and not birth:errors["fecha_nacimiento"]="Ingresa una fecha válida."
        if birth and (date.today().year-birth.year-((date.today().month,date.today().day)<(birth.month,birth.day)))<18:errors["fecha_nacimiento"]="El empleado debe tener al menos 18 años."
        if data.get("curp") and not validar_curp(data["curp"],birth):errors["curp"]="La CURP no es válida o no coincide con la fecha de nacimiento."
        if data.get("rfc") and not validar_rfc_persona_fisica(data["rfc"]):errors["rfc"]="El RFC de persona física no es válido."
        if data.get("email_trabajo") and (not EMAIL.fullmatch(data["email_trabajo"]) or data["email_trabajo"]==data["email"]):errors["email_trabajo"]="Usa un correo válido y distinto del personal."
        hire=_date(data.get("fecha_ingreso"))
        if data.get("fecha_ingreso") and (not hire or hire>date.today()):errors["fecha_ingreso"]="La fecha de ingreso no puede ser futura."
        data["fecha_nacimiento"]=birth
        data["fecha_ingreso"]=hire
        return data,errors
