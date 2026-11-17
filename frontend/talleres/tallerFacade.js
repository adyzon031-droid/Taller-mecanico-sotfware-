import {TallerRepository} from './tallerRepository.js';
import {normalizarPalabras,validarRfc} from '../clientes/clienteFacade.js';
export class TallerFacade{
 constructor(repository=new TallerRepository()){this.repository=repository}
 validar(d){const e={};for(const k of ['nombre','razon_social','rfc','email_contacto','telefono','calle','colonia','municipio','estado','codigo_postal'])if(!String(d[k]||'').trim())e[k]='Este campo es obligatorio.';if(d.rfc&&!validarRfc(d.rfc)&&!(/^[A-Z&Ñ]{3}\d{6}[A-Z0-9]{3}$/.test(String(d.rfc).toUpperCase())))e.rfc='RFC inválido.';if(d.email_contacto&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.email_contacto))e.email_contacto='Correo inválido.';if(d.codigo_postal&&!/^\d{5}$/.test(d.codigo_postal))e.codigo_postal='Usa cinco dígitos.';if(d.foto&&(!/\.(jpg|jpeg|png|webp)$/i.test(d.foto.name)||!['image/jpeg','image/png','image/webp'].includes(d.foto.type)||d.foto.size>15*1024*1024))e.foto='Foto JPG, PNG o WEBP de máximo 15 MB.';return e}
 normalizar(d){const r={...d};for(const k of ['nombre','razon_social','calle','colonia','municipio','estado','direccion_temporal_calle','direccion_temporal_colonia','direccion_temporal_municipio','direccion_temporal_estado'])r[k]=normalizarPalabras(r[k]);r.rfc=String(r.rfc||'').trim().toUpperCase();r.email_contacto=String(r.email_contacto||'').trim().toLowerCase();r.telefono=String(r.telefono||'').replace(/\D/g,'');delete r.foto;return r}
 listar(filters){return this.repository.listar(filters)} consultar(id){return this.repository.consultar(id)}
 async guardar(id,data){const errors=this.validar(data);if(Object.keys(errors).length)throw Object.assign(new Error('Revisa los campos.'),{status:422,fieldErrors:errors});const values=this.normalizar(data);let result=id?await this.repository.actualizar(id,values):await this.repository.crear(values);if(data.foto){const key=result.id||id;await this.repository.foto(key,data.foto)}return result}
 estado(id,activo,motivo){return this.repository.estado(id,activo,motivo)}
}
