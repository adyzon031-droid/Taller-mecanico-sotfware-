"""Validación de clientes y reglas de alcance por taller."""
from datetime import date
import re
import phonenumbers
from identidad_mexico import normalizar_palabras, validar_curp, validar_rfc_persona_fisica

class ClienteError(ValueError):
    def __init__(self,message,status=422,errors=None):
        super().__init__(message);self.status=status;self.errors=errors or {}

EMAIL=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
REQUIRED=("nombres","apellido_paterno","fecha_nacimiento","curp","celular","email","calle","colonia","municipio","estado","codigo_postal")
LIMITS={"nombres":180,"apellido_paterno":100,"apellido_materno":100,"email":190,"email_trabajo":190,"calle":180,"numero_interior":30,"colonia":120,"municipio":120,"estado":120,"curp":18,"rfc":13}
PHONE_FIELDS=("celular","telefono_fijo","telefono_trabajo")


def normalizar_texto(v):return re.sub(r"\s+"," ",str(v or "")).strip()
def edad_desde_fecha(nacimiento,hoy=None):
    hoy=hoy or date.today();return hoy.year-nacimiento.year-((hoy.month,hoy.day)<(nacimiento.month,nacimiento.day))


def validar(data,hoy=None,ubicacion_repository=None,legacy=False):
    if not isinstance(data,dict):raise ClienteError("El cuerpo debe ser un objeto JSON",errors={"_global":"El cuerpo debe ser un objeto JSON."})
    clean={k:normalizar_texto(v) if v is not None else "" for k,v in data.items()}
    errors={}
    # Alias de compatibilidad con formularios/registros previos.
    if not clean.get("celular") and clean.get("telefono_personal"):clean["celular"]=clean["telefono_personal"]
    if not clean.get("celular_prefijo"):clean["celular_prefijo"]=clean.get("telefono_personal_prefijo","52")
    if not clean.get("celular_pais"):clean["celular_pais"]=clean.get("telefono_personal_pais","MX")
    for field in ("nombres","apellido_paterno","apellido_materno","calle","colonia","municipio","estado"):
        if legacy and field=="nombres" and not clean.get("apellido_paterno") and not clean.get("apellido_materno"):
            clean[field]=normalizar_texto(clean.get(field))
        else:
            clean[field]=normalizar_palabras(clean.get(field))
    clean["email"]=(clean.get("email") or "").lower();clean["email_trabajo"]=(clean.get("email_trabajo") or "").lower()
    clean["curp"]=(clean.get("curp") or "").upper();clean["rfc"]=(clean.get("rfc") or "").upper()
    raw_contact=data.get("contacto") if isinstance(data.get("contacto"),dict) else {}
    contact={k:normalizar_texto(v) if v is not None else "" for k,v in raw_contact.items()}
    contact["nombre"]=normalizar_palabras(contact.get("nombre"))
    contact["email"]=(contact.get("email") or "").lower();contact["email_trabajo"]=(contact.get("email_trabajo") or "").lower()
    for key in REQUIRED:
        if not clean.get(key) and not (legacy and key in ("apellido_paterno","curp")):
            errors[key]="Este campo es obligatorio."
    if clean.get("nombres") and not re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*",clean["nombres"]):
        errors["nombres"]="Ingresa nombres válidos."
    if clean.get("contacto_alterno") and not re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*",clean["contacto_alterno"]):
        errors["contacto_alterno"]="Ingresa un nombre válido."
    if not contact.get("nombre"):errors["contacto.nombre"]="El nombre del contacto es obligatorio."
    elif not re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*",contact["nombre"]):errors["contacto.nombre"]="Ingresa un nombre válido."
    for field in ("telefono_personal","email"):
        if not contact.get(field):errors[f"contacto.{field}"]="Este campo es obligatorio."
    for key in ("apellido_paterno","apellido_materno"):
        if clean.get(key) and not re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*",clean[key]):errors[key]="Ingresa un apellido válido."
    if clean.get("fecha_nacimiento"):
        try:birth=date.fromisoformat(clean["fecha_nacimiento"][:10])
        except ValueError:birth=None;errors["fecha_nacimiento"]="Ingresa una fecha real."
        if birth:
            age=edad_desde_fecha(birth,hoy)
            if birth>(hoy or date.today()) or age>120:errors["fecha_nacimiento"]="La fecha debe estar en el rango permitido."
            if clean.get("edad") not in (None,"") and str(clean.get("edad"))!=str(age):errors["edad"]="La edad no coincide con la fecha de nacimiento."
            clean["edad"]=age
            if clean.get("curp") and not validar_curp(clean["curp"],birth.isoformat()):errors["curp"]="La CURP es inválida o no coincide con la fecha de nacimiento."
    elif clean.get("curp") and not validar_curp(clean["curp"]):errors["curp"]="La CURP no tiene estructura o dígito verificador válido."
    if clean.get("curp") and not validar_curp(clean["curp"],clean.get("fecha_nacimiento") or None):errors["curp"]="La CURP es inválida o no coincide con la fecha de nacimiento."
    if clean.get("rfc") and not validar_rfc_persona_fisica(clean["rfc"]):errors["rfc"]="El RFC debe ser válido para persona física (13 caracteres)."
    for field in PHONE_FIELDS:
        clean.setdefault(field+"_prefijo","52");clean.setdefault(field+"_pais","MX")
        number=clean.get(field) or ""
        prefix=(clean.get(field+"_prefijo") or "52").replace("+","")
        region=(clean.get(field+"_pais") or "MX").upper()
        if number:
            if not re.fullmatch(r"[\d\s()\-]+",number):errors[field]="Ingresa un teléfono válido.";continue
            digits=re.sub(r"\D","",number)
            try:
                if not re.fullmatch(r"\d{1,3}",prefix) or phonenumbers.country_code_for_region(region)!=int(prefix):raise ValueError
                parsed=phonenumbers.parse("+"+prefix+digits,region)
                if not phonenumbers.is_valid_number_for_region(parsed,region):raise ValueError
                if prefix=="52" and len(digits)!=10:raise ValueError
                clean[field]=digits;clean[field+"_prefijo"]=prefix;clean[field+"_pais"]=region
            except (ValueError,phonenumbers.NumberParseException):errors[field]="Ingresa un teléfono válido para el país seleccionado."
        else:clean[field]=None
    for field in ("telefono_personal","telefono_trabajo"):
        number=contact.get(field) or ""
        prefix=(contact.get(field+"_prefijo") or "52").replace("+","")
        region=(contact.get(field+"_pais") or "MX").upper()
        if number:
            if not re.fullmatch(r"[\d\s()\-]+",number):errors[f"contacto.{field}"]="Ingresa un teléfono válido.";continue
            digits=re.sub(r"\D","",number)
            try:
                if not re.fullmatch(r"\d{1,3}",prefix) or phonenumbers.country_code_for_region(region)!=int(prefix):raise ValueError
                parsed=phonenumbers.parse("+"+prefix+digits,region)
                if not phonenumbers.is_valid_number_for_region(parsed,region) or (prefix=="52" and len(digits)!=10):raise ValueError
                contact[field]=digits;contact[field+"_prefijo"]=prefix;contact[field+"_pais"]=region
            except (ValueError,phonenumbers.NumberParseException):errors[f"contacto.{field}"]="Ingresa un teléfono válido para el país seleccionado."
        else:
            contact[field]=None;contact[field+"_prefijo"]=None;contact[field+"_pais"]=None
    clean["telefono_personal"]=clean.get("celular");clean["telefono_personal_prefijo"]=clean.get("celular_prefijo");clean["telefono_personal_pais"]=clean.get("celular_pais")
    for field in ("email","email_trabajo"):
        if clean.get(field) and (len(clean[field])>190 or not EMAIL.fullmatch(clean[field])):errors[field]="Ingresa un correo válido."
        if contact.get(field) and (len(contact[field])>190 or not EMAIL.fullmatch(contact[field])):errors[f"contacto.{field}"]="Ingresa un correo válido."
    if clean.get("email_trabajo") and clean["email_trabajo"]==clean.get("email"):errors["email_trabajo"]="Debe ser distinto del correo personal."
    if contact.get("email_trabajo") and contact["email_trabajo"]==contact.get("email"):errors["contacto.email_trabajo"]="Debe ser distinto del correo del contacto."
    if contact.get("telefono_personal") and (contact.get("telefono_personal_prefijo"),contact["telefono_personal"])==(clean.get("celular_prefijo"),clean.get("celular")):
        errors["contacto.telefono_personal"]="Debe ser distinto del teléfono personal del cliente."
    if contact.get("email") and contact["email"]==clean.get("email"):
        errors["contacto.email"]="Debe ser distinto del correo electrónico del cliente."
    state_names={"Aguascalientes","Baja California","Baja California Sur","Campeche","Chiapas","Chihuahua","Ciudad de México","Coahuila","Colima","Durango","Estado de México","Guanajuato","Guerrero","Hidalgo","Jalisco","Michoacán","Morelos","Nayarit","Nuevo León","Oaxaca","Puebla","Querétaro","Quintana Roo","San Luis Potosí","Sinaloa","Sonora","Tabasco","Tamaulipas","Tlaxcala","Veracruz","Yucatán","Zacatecas"}
    if clean.get("estado") and clean["estado"] not in state_names:errors["estado"]="Selecciona un estado de México."
    if clean.get("codigo_postal") and not re.fullmatch(r"\d{5}",clean["codigo_postal"]):errors["codigo_postal"]="Usa cinco dígitos."
    clean["colonia_manual"]=str(data.get("colonia_manual",False)).lower() in ("1","true","yes")
    if ubicacion_repository and not errors and not clean["colonia_manual"] and ubicacion_repository.catalogo_cargado() and not ubicacion_repository.direccion_valida(clean["estado"],clean["municipio"],clean["colonia"],clean["codigo_postal"]):errors["codigo_postal"]="La combinación postal no existe en SEPOMEX."
    for field,limit in LIMITS.items():
        if len(clean.get(field) or "")>limit:errors[field]=f"Máximo {limit} caracteres."
    clean["nombre_completo"]=" ".join(x for x in (clean.get("nombres"),clean.get("apellido_paterno"),clean.get("apellido_materno")) if x)
    clean["contacto"]=contact
    clean.setdefault("contacto_alterno",None)
    if len(clean["nombre_completo"])>180:errors["nombres"]="El nombre completo no puede superar 180 caracteres."
    clean["datos_por_completar"]=int(bool(legacy and (not clean.get("apellido_paterno") or not clean.get("curp"))))
    if errors:raise ClienteError("Revisa los campos indicados.",errors=errors)
    return clean

class ClienteFacade:
    def __init__(self,repository,ubicacion_repository=None,taller_repository=None):self.repository=repository;self.ubicacion_repository=ubicacion_repository;self.ubicacion_service=None;self.taller_repository=taller_repository
    def _validated(self,data,legacy=False):
        clean=validar(data,ubicacion_repository=None if self.ubicacion_service else self.ubicacion_repository,legacy=legacy)
        service=self.ubicacion_service
        if service and not clean.get('colonia_manual') and not service.direccion_valida(clean['estado'],clean['municipio'],clean['colonia'],clean['codigo_postal']):
            raise ClienteError('Revisa los campos indicados.',errors={'codigo_postal':'La combinación postal no existe en SEPOMEX.'})
        return clean
    def _target_workshop(self,data,session_user):
        if session_user["rol"]=="recepcionista":return session_user["taller_id"]
        if session_user["rol"]=="administrador" and not data.get("taller_id"):
            raise ClienteError("Selecciona un taller.",errors={"taller_id":"Selecciona un taller activo."})
        try:target=int(data.get("taller_id") or session_user["taller_id"])
        except (ValueError,TypeError):raise ClienteError("Selecciona un taller válido.",errors={"taller_id":"Selecciona un taller activo."})
        if not self.repository.taller_de_empresa(target,session_user["taller_id"]):raise ClienteError("Taller no disponible en la empresa.",403)
        return target
    def crear(self,data,session_user,foto_contexto=None,foto_ruta=None):
        values=self._validated(data);values.update(taller_id=self._target_workshop(data,session_user),creado_por=session_user["usuario_id"],foto_ruta=foto_ruta)
        if self.repository.duplicado(values["taller_id"],values):raise ClienteError("Ya existe un cliente con esos datos.",409)
        return self.repository.crear(values,foto_contexto)
    def listar(self,session_user,filters,page=1,page_size=10,sort="fecha",direction="desc",status="activo"):
        return self.repository.listar(session_user,filters,page,page_size,sort,direction,status)
    def obtener(self,session_user,client_id):return self.repository.obtener(session_user,client_id)
    def actualizar(self,session_user,client_id,data,foto_contexto=None,foto_ruta=None):
        current=self.repository.obtener(session_user,client_id)
        if not current:return False
        if current.get("estado_cliente")=="suspendido":raise ClienteError("El cliente está suspendido; reactívalo antes de editar.",409)
        values=self._validated(data,legacy=bool(current.get("datos_por_completar")))
        values["taller_id"]=current["taller_id"]
        # El teléfono fijo se retiró de la vista; conservar su valor legado al editar.
        for key in ("telefono_fijo","telefono_fijo_prefijo","telefono_fijo_pais","contacto_alterno"):
            values[key]=current.get(key)
        if session_user["rol"]=="administrador":values["taller_id"]=self._target_workshop(data,session_user)
        values.update(foto_ruta=foto_ruta if foto_ruta is not None else current.get("foto_ruta"))
        if self.repository.duplicado(values["taller_id"],values,client_id):raise ClienteError("Ya existe un cliente con esos datos.",409)
        return self.repository.actualizar(session_user,client_id,values,foto_contexto)
    def suspender(self,session_user,client_id,user_id,reason=None):
        if session_user["rol"]!="administrador":raise ClienteError("Permiso insuficiente",403)
        return self.repository.estado(session_user,client_id,"suspendido",user_id,reason)
    def reactivar(self,session_user,client_id,user_id):
        if session_user["rol"]!="administrador":raise ClienteError("Permiso insuficiente",403)
        return self.repository.estado(session_user,client_id,"activo",user_id,None)
    def eliminar(self,session_user,client_id):
        if session_user["rol"]!="administrador":raise ClienteError("Permiso insuficiente",403)
        return self.repository.eliminar(session_user,client_id)
