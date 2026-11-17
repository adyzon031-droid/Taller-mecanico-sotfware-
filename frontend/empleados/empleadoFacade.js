import {EmpleadoRepository} from './empleadoRepository.js';
/** Reglas de interfaz y coordinación del módulo de empleados. */
export class EmpleadoFacade {
  constructor(repository=new EmpleadoRepository()){this.repository=repository;}
  listar(filters){return this.repository.listar(filters);}
  talleres(){return this.repository.talleres();}
  consultar(id){return this.repository.consultar(id);}
  verificar(campo,valor,exclude){return this.repository.verificar(campo,valor,exclude);}
  guardar(id,data,photo){
    const errors={};
    if(!id&&!String(data.apellido_paterno||'').trim())errors.apellido_paterno='Ingresa el apellido paterno.';
    if(!id&&!String(data.telefono_personal||'').trim())errors.telefono_personal='Ingresa el teléfono personal.';
    if(!String(data.email||'').includes('@'))errors.email='Ingresa un correo válido.';
    if(!data.rol)errors.rol='Selecciona un rol.';
    if(!data.taller_id)errors.taller_id='Selecciona un taller.';
    if(!id&&String(data.password||'').length<12)errors.password='La contraseña requiere al menos 12 caracteres.';
    if(data.password&&data.password!==data.password_confirm)errors.password_confirm='Las contraseñas no coinciden.';
    if(Object.keys(errors).length){const e=new Error('Revisa los campos del empleado.');e.status=422;e.errors=errors;throw e;}
    return this.repository.guardar(id,data,photo);
  }
  estado(id,active,reason){return this.repository.estado(id,active,reason);}
}
