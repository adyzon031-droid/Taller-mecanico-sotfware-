"""Reglas para alta, edición, catálogo y suspensión de talleres."""
import re
import phonenumbers
from cliente_facade import ClienteError
from identidad_mexico import normalizar_palabras, validar_rfc_persona_fisica
from taller_repository import FIELDS

EMAIL=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

class TallerFacade:
    def __init__(self,repository,ubicacion_repository):self.repository=repository;self.ubicacion=ubicacion_repository

    def _validate(self,data):
        values={k:(str(data.get(k) or '').strip() or None) for k in FIELDS}
        values['nombre']=normalizar_palabras(values['nombre'] or '')
        values['razon_social']=normalizar_palabras(values['razon_social'] or '')
        for field in ('calle','colonia','municipio','estado','direccion_temporal_calle','direccion_temporal_colonia','direccion_temporal_municipio','direccion_temporal_estado'):
            values[field]=normalizar_palabras(values.get(field) or '') or None
        values['rfc']=(values['rfc'] or '').upper()
        values['email_contacto']=(values['email_contacto'] or '').lower()
        for key in ('colonia_manual','direccion_temporal_colonia_manual'):
            values[key] = str(data.get(key, False)).lower() in ('1','true','yes')
        errors={}
        for k in ('nombre','razon_social','rfc','email_contacto','telefono','calle','colonia','municipio','estado','codigo_postal'):
            if not values[k]:errors[k]='Este campo es obligatorio.'
        rfc=values['rfc'] or ''
        if rfc and not (validar_rfc_persona_fisica(rfc) or re.fullmatch(r'[A-Z&Ñ]{3}\d{6}[A-Z0-9]{3}',rfc)):
            errors['rfc']='Ingresa un RFC válido de 12 caracteres (persona moral) o 13 (persona física).'
        email=values['email_contacto'] or ''
        if email and (len(email)>190 or not EMAIL.fullmatch(email)):errors['email_contacto']='Ingresa un correo válido de máximo 190 caracteres.'
        for field,limit in (("nombre",160),("razon_social",180),("calle",180),("numero_interior",30),("colonia",120),("municipio",120),("estado",120)):
            if len(values.get(field) or "")>limit:errors[field]="Máximo "+str(limit)+" caracteres."
        phone=values['telefono'] or ''
        if phone:
            prefix=(values['telefono_prefijo'] or '52').replace('+','')
            region=(values['telefono_pais'] or 'MX').upper()
            try:
                parsed=phonenumbers.parse('+'+prefix+re.sub(r'\D','',phone),region)
                if not phonenumbers.is_valid_number_for_region(parsed,region):raise ValueError
                values['telefono']=re.sub(r'\D','',phone);values['telefono_prefijo']=prefix;values['telefono_pais']=region
            except (ValueError,phonenumbers.NumberParseException):errors['telefono']='Ingresa un teléfono válido para el país seleccionado.'
        if values['codigo_postal'] and not re.fullmatch(r'\d{5}',values['codigo_postal']):errors['codigo_postal']='Usa cinco dígitos.'
        if values['estado']:values['estado']=normalizar_palabras(values['estado'])
        for prefix in ('','direccion_temporal_'):
            cp=values.get(prefix+'codigo_postal')
            address=(values.get(prefix+'estado'),values.get(prefix+'municipio'),values.get(prefix+'colonia'),cp)
            required=prefix==''
            manual=values.get(prefix+'colonia_manual',False)
            if required and all(address) and not self.ubicacion.direccion_valida(address[0],address[1],address[2],address[3],manual):
                errors['codigo_postal']='La combinación de código postal y dirección no existe en SEPOMEX.'
            if not required and any(address) and not all(address):errors['direccion_temporal_codigo_postal']='Completa todos los campos de la dirección temporal.'
            if not required and all(address) and not self.ubicacion.direccion_valida(address[0],address[1],address[2],address[3],manual):errors['direccion_temporal_codigo_postal']='La dirección temporal no coincide con SEPOMEX.'
        if errors:raise ClienteError('Revisa los campos indicados.',errors=errors)
        return values

    def listar(self,session_user):return self.repository.listar(session_user)
    def obtener(self,session_user,taller_id):return self.repository.obtener(session_user,taller_id)
    def crear(self,session_user,data):
        if session_user['rol']!='administrador':raise ClienteError('Permiso insuficiente',403)
        values=self._validate(data);return self.repository.crear(session_user,values)
    def actualizar(self,session_user,taller_id,data):
        if session_user['rol']!='administrador':raise ClienteError('Permiso insuficiente',403)
        values=self._validate(data);return self.repository.actualizar(session_user,taller_id,values)
    def set_estado(self,session_user,taller_id,active,user_id,reason=None):
        if session_user['rol']!='administrador':raise ClienteError('Permiso insuficiente',403)
        return self.repository.estado(session_user,taller_id,active,user_id,reason)
