import { EstatusRepository } from './estatusRepository.js';
/** Coordina operaciones del catálogo y notificaciones visuales. */
export class EstatusFacade {
  constructor(repository = new EstatusRepository(), notify = () => {}) { this.repository = repository; this.notify = notify; }
  listar(params) { return this.repository.list(params); }
  opciones() { return this.repository.options(); }
  guardar(id, data) {
    const valor = String(data.valor || '').trim().toLocaleLowerCase('es-MX').replace(/\s+/g, ' ');
    const descripcion = String(data.descripcion || '').trim().replace(/\s+/g, ' ');
    const errors = {};
    if (!/^[\p{L}]+(?: [\p{L}]+)*$/u.test(valor) || valor.length < 3 || valor.length > 30) errors.valor = 'Usa de 3 a 30 letras y espacios.';
    if (descripcion.length < 5 || descripcion.length > 255) errors.descripcion = 'Usa de 5 a 255 caracteres.';
    if (Object.keys(errors).length) throw Object.assign(new Error('Revisa los campos indicados.'), { status: 422, errors });
    return this.repository.save(id, { valor, descripcion });
  }
  estado(id, active) { return this.repository.activate(id, active); }
}
