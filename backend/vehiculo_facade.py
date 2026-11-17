"""Validaciones de vehículos; las reglas se repiten en el backend como autoridad."""
import re
from datetime import date, datetime, timedelta
from vehiculo_catalogo_facade import normalizar_nombre
from estatus_facade import StatusError


class VehicleError(ValueError):
    def __init__(self, message, status=422, errors=None, code=None):
        super().__init__(message); self.status=status; self.errors=errors or {}; self.code=code; self.warnings=[]


class VehiculoFacade:
    def __init__(self, repository, catalog_repository): self.repository=repository; self.catalog=catalog_repository

    @staticmethod
    def validate(data, today=None):
        if not isinstance(data,dict): raise VehicleError("El cuerpo debe ser un objeto JSON.",errors={"_global":"El cuerpo debe ser un objeto JSON."})
        today=today or date.today(); d=dict(data); errors={}; warnings=[]
        d['placa']=re.sub(r"[-\s]",'',str(d.get('placa') or '')).upper()
        d['marca']=normalizar_nombre(d.get('marca') or d.get('marca_texto'))
        d['modelo']=normalizar_nombre(d.get('modelo') or d.get('modelo_texto')) or None
        d['version']=normalizar_nombre(d.get('version')) or None
        d['numero_serie']=re.sub(r"[-\s]",'',str(d.get('numero_serie') or '')).upper() or None
        if not re.fullmatch(r'[A-Z0-9]{5,8}',d['placa']): errors['placa']='Usa de 5 a 8 letras o números.'
        if not d['marca']: errors['marca']='Selecciona o escribe una marca.'
        try:d['cliente_id']=int(d.get('cliente_id')); assert d['cliente_id']>0
        except (TypeError,ValueError,AssertionError):errors['cliente_id']='Selecciona un cliente válido.'
        try: year=int(d.get('anio')); d['anio']=year
        except (ValueError,TypeError): year=0; d['anio']=None
        if not 1900<=year<=today.year+1: errors['anio']=f'Usa un año entre 1900 y {today.year+1}.'
        try: entered=date.fromisoformat(str(d.get('fecha_ingreso') or '')[:10])
        except ValueError: entered=None
        if not entered: errors['fecha_ingreso']='La fecha de ingreso es obligatoria y debe ser válida.'
        elif entered>today or entered<today-timedelta(days=365): errors['fecha_ingreso']='La fecha debe estar dentro del último año y no ser futura.'
        elif entered<today-timedelta(days=30): warnings.append({'campo':'fecha_ingreso','mensaje':'La fecha de ingreso tiene más de 30 días.'})
        if d['numero_serie'] and not re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}',d['numero_serie']): errors['numero_serie']='El VIN debe tener 17 caracteres válidos.'
        elif d['numero_serie']:
            trans={**{str(i):i for i in range(10)},**dict(zip('ABCDEFGH',range(1,9))),**dict(zip('JKLMNPR',range(1,8))),**{'S':2,'T':3,'U':4,'V':5,'W':6,'X':7,'Y':8,'Z':9}}
            weights=[8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2]
            check=sum(trans[ch]*weights[i] for i,ch in enumerate(d['numero_serie']))%11
            if ('X' if check==10 else str(check))!=d['numero_serie'][8]: warnings.append({'campo':'numero_serie','mensaje':'El dígito verificador del VIN no coincide.'})
            year_codes=dict(zip('ABCDEFGHJKLMNPRSTVWXY',range(1980,2001)))
            code=d['numero_serie'][9]
            if code in year_codes and year and year_codes[code] + max(0,(year-year_codes[code])//30)*30 != year: warnings.append({'campo':'numero_serie','mensaje':'El año del VIN no coincide con el año capturado.'})
        try: km=None if d.get('kilometraje') in (None,'') else int(d['kilometraje']); d['kilometraje']=km
        except (ValueError,TypeError): km=-1
        if km is not None and not 0<=km<=2_000_000: errors['kilometraje']='Usa un entero entre 0 y 2 000 000.'
        if km is not None and year:
            age=max(0,today.year-year)
            if age and km>age*60_000:warnings.append({'campo':'kilometraje','mensaje':'El kilometraje supera 60 000 km por año de antigüedad.'})
            if age<=2 and km>20_000:warnings.append({'campo':'kilometraje','mensaje':'El kilometraje es alto para un vehículo reciente.'})
        if d.get('version') and len(d['version'])>40: errors['version']='Máximo 40 caracteres.'
        if errors: raise VehicleError('Revisa los campos indicados.',422,errors)
        d['_warnings']=warnings
        return d

    def create(self,user,data):
        clean=self.validate(data)
        allow_exception=bool(data.get('permitir_excepcion'))
        reason=str(data.get('motivo_excepcion') or '').strip()
        if allow_exception:
            if user.get('rol')!='administrador': raise VehicleError('Solo administración puede registrar con excepción.',403)
            if len(reason)<10: raise VehicleError('Indica un motivo de al menos 10 caracteres.',422,{'motivo_excepcion':'Indica un motivo de al menos 10 caracteres.'})
        clean['permitir_excepcion']=allow_exception;clean['motivo_excepcion']=reason
        return self.repository.create(user,clean)

    @staticmethod
    def validar_activacion(data, today=None):
        """Normaliza la ficha y exige los datos opcionales antes de activarla."""
        clean = VehiculoFacade.validate(data, today=today)
        errors = {}
        for field, message in {
            "modelo": "El modelo es obligatorio para activar el vehículo.",
            "version": "La versión es obligatoria para activar el vehículo.",
            "numero_serie": "El VIN es obligatorio para activar el vehículo.",
        }.items():
            if not clean.get(field):
                errors[field] = message
        if clean.get("kilometraje") is None:
            errors["kilometraje"] = "El kilometraje es obligatorio para activar el vehículo."
        if errors:
            raise VehicleError("Completa la ficha antes de activar el vehículo.", 422, errors)
        return clean

    @staticmethod
    def validar_desactivacion(data):
        """Valida la confirmación explícita y el motivo de la baja lógica."""
        if not isinstance(data, dict):
            raise VehicleError("El cuerpo debe ser un objeto JSON.", 422, {"_global": "El cuerpo debe ser un objeto JSON."})
        motivo = " ".join(str(data.get("motivo") or "").split())
        errors = {}
        if data.get("confirmado") is not True:
            errors["confirmado"] = "Confirma la desactivación del vehículo."
        if not 3 <= len(motivo) <= 500:
            errors["motivo"] = "Indica un motivo de 3 a 500 caracteres."
        if errors:
            raise VehicleError("Revisa los campos indicados.", 422, errors)
        return {"motivo": motivo}

    @staticmethod
    def validar_relacion(data, cambio_propietario=False, today=None):
        if not isinstance(data,dict): raise VehicleError('El cuerpo debe ser un objeto JSON.',422,{'_global':'El cuerpo debe ser un objeto JSON.'})
        today=today or date.today(); errors={}; result=dict(data)
        try: result['cliente_id']=int(data.get('cliente_id',data.get('cliente_nuevo_id'))); assert result['cliente_id']>0
        except (TypeError,ValueError,AssertionError): errors['cliente_id']='Selecciona un cliente válido.'
        relation=result.get('tipo_relacion','propietario')
        if relation not in ('propietario','conductor habitual','responsable de pago'): errors['tipo_relacion']='Selecciona un tipo de relación válido.'
        result['tipo_relacion']=relation
        date_key='fecha_efectiva' if cambio_propietario else 'fecha_inicio'
        try: result[date_key]=date.fromisoformat(str(data.get(date_key) or '')[:10])
        except ValueError: errors[date_key]='La fecha es obligatoria y debe ser válida.'
        if result.get(date_key) and result[date_key]>today: errors[date_key]='La fecha no puede ser futura.'
        result['motivo']=str(data.get('motivo') or '').strip()
        if cambio_propietario and len(result['motivo'])<10: errors['motivo']='Indica un motivo de al menos 10 caracteres.'
        if errors: raise VehicleError('Revisa los campos indicados.',422,errors)
        return result
