import { ClienteRepository } from './clienteRepository.js';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const NOMBRE = /^[\p{L}]+(?:[ '-][\p{L}]+)+$/u;
const ESTADOS = new Set([
  'Aguascalientes','Baja California','Baja California Sur','Campeche','Chiapas','Chihuahua',
  'Ciudad de México','Coahuila','Colima','Durango','Estado de México','Guanajuato','Guerrero',
  'Hidalgo','Jalisco','Michoacán','Morelos','Nayarit','Nuevo León','Oaxaca','Puebla','Querétaro',
  'Quintana Roo','San Luis Potosí','Sinaloa','Sonora','Tabasco','Tamaulipas','Tlaxcala',
  'Veracruz','Yucatán','Zacatecas',
]);
const TEXT_FIELDS = ['nombre_completo','contacto_alterno','calle','colonia','municipio','estado'];

export function edadDe(fecha, hoy = new Date()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha || '')) return null;
  const [year, month, day] = fecha.split('-').map(Number);
  const birth = new Date(year, month - 1, day);
  if (birth.getFullYear() !== year || birth.getMonth() !== month - 1 || birth.getDate() !== day) return null;
  let age = hoy.getFullYear() - year;
  if (hoy.getMonth() + 1 < month || (hoy.getMonth() + 1 === month && hoy.getDate() < day)) age--;
  return age;
}

export function normalizarCliente(cliente) {
  const result = { ...cliente };
  for (const key of TEXT_FIELDS) result[key] = String(result[key] ?? '').trim().replace(/\s+/g, ' ');
  result.email = String(result.email ?? '').trim().toLowerCase();
  result.email_trabajo = String(result.email_trabajo ?? '').trim().toLowerCase();
  for (const key of ['telefono_personal','telefono_trabajo']) result[key] = String(result[key] ?? '').replace(/\D/g, '').slice(0, 10);
  const age = edadDe(String(result.fecha_nacimiento ?? ''));
  if (age !== null) result.edad = age;
  return result;
}

/** Facade: valida, coordina CRUD y notifica; la vista nunca llama a fetch. */
export class ClienteFacade {
  constructor(repository = new ClienteRepository(), notificar = () => {}) {
    this.repository = repository;
    this.notificar = notificar;
  }

  errores(cliente) {
    const c = normalizarCliente(cliente);
    const errors = {};
    const required = ['nombre_completo','fecha_nacimiento','telefono_personal','telefono_trabajo','email','calle','colonia','municipio','estado','codigo_postal'];
    for (const key of required) if (!c[key]) errors[key] = 'Este campo es obligatorio.';
    for (const key of ['nombre_completo','contacto_alterno']) {
      if (c[key] && !NOMBRE.test(c[key])) errors[key] = 'Escribe al menos dos palabras, solo con letras, espacios, apóstrofo o guion.';
    }
    for (const key of ['telefono_personal','telefono_trabajo']) {
      const raw = String(cliente[key] ?? '');
      if (c[key] && (/[^\d\s()-]/.test(raw) || c[key].length !== 10)) errors[key] = 'Ingresa 10 dígitos.';
    }
    for (const key of ['email','email_trabajo']) {
      if (c[key] && (c[key].length > 190 || !EMAIL.test(c[key]))) errors[key] = 'Escribe un correo válido de máximo 190 caracteres.';
    }
    if (c.email_trabajo && c.email_trabajo === c.email) errors.email_trabajo = 'Debe ser distinto al correo personal.';
    const age = edadDe(String(c.fecha_nacimiento || ''));
    if (c.fecha_nacimiento && age === null) errors.fecha_nacimiento = 'Ingresa una fecha real.';
    else if (age !== null && (age < 0 || age > 120)) errors.fecha_nacimiento = 'La fecha debe tener entre 0 y 120 años.';
    if (age !== null && cliente.edad != null && cliente.edad !== '' && Number(cliente.edad) !== age) errors.edad = 'La edad no coincide con la fecha de nacimiento.';
    if (c.codigo_postal && !/^\d{5}$/.test(c.codigo_postal)) errors.codigo_postal = 'Usa cinco dígitos.';
    if (c.estado && !ESTADOS.has(c.estado)) errors.estado = 'Selecciona un estado de México.';
    const limits = { nombre_completo:180, contacto_alterno:180, calle:180, colonia:120, municipio:120, estado:120 };
    for (const [key, limit] of Object.entries(limits)) if (c[key].length > limit) errors[key] = `Máximo ${limit} caracteres.`;
    const photo = cliente.foto;
    if (photo) {
      if (!/\.(jpg|jpeg|png|webp)$/i.test(photo.name) || !['image/jpeg','image/png','image/webp'].includes(photo.type)) errors.foto = 'Formato inválido. Usa JPG, JPEG, PNG o WEBP.';
      else if (photo.size > 15 * 1024 * 1024) errors.foto = 'El máximo permitido es 15 MB.';
    }
    return errors;
  }

  preparar(cliente) {
    const errors = this.errores(cliente);
    if (Object.keys(errors).length) throw Object.assign(new Error(Object.values(errors)[0]), { fieldErrors: errors, status: 422 });
    const { foto, ...payload } = normalizarCliente(cliente);
    delete payload.id;
    return { payload, foto: foto || null };
  }

  async verificarDuplicado(cliente, excluirId = null) {
    const c = normalizarCliente(cliente);
    return this.repository.verificarDuplicado({
      email: c.email, telefono_personal: c.telefono_personal,
      nombre_completo: c.nombre_completo, fecha_nacimiento: c.fecha_nacimiento,
      ...(excluirId ? { excluir_id: excluirId } : {}),
    });
  }

  async registrar(cliente) {
    try {
      const { payload, foto } = this.preparar(cliente);
      if ((await this.verificarDuplicado(payload)).duplicado) throw Object.assign(new Error('Ya existe un cliente con esos datos.'), { status: 409 });
      const result = await this.repository.crear(payload, foto);
      this.notificar('Cliente registrado correctamente.', 'success');
      return result;
    } catch (error) {
      this.notificar(this.mensaje(error, 'registrar'), 'error');
      throw error;
    }
  }

  async actualizar(id, cliente) {
    try {
      const { payload, foto } = this.preparar(cliente);
      if ((await this.verificarDuplicado(payload, id)).duplicado) throw Object.assign(new Error('Ya existe un cliente con esos datos.'), { status: 409 });
      const result = await this.repository.actualizar(id, payload, foto);
      this.notificar('Cliente actualizado correctamente.', 'success');
      return result;
    } catch (error) {
      this.notificar(this.mensaje(error, 'actualizar'), 'error');
      throw error;
    }
  }

  async eliminar(id) {
    try {
      const result = await this.repository.eliminar(id);
      this.notificar('Cliente eliminado correctamente.', 'success');
      return result;
    } catch (error) {
      this.notificar(this.mensaje(error, 'eliminar'), 'error');
      throw error;
    }
  }

  listar(filtros = {}) { return this.repository.listar(filtros); }
  consultar(id) { return this.repository.consultar(id); }

  mensaje(error, action) {
    if (error.status === 409) return 'Registro duplicado: revisa correo, teléfono y nombre/fecha.';
    if (error.status === 403) return 'No tienes permiso para realizar esta acción.';
    if (error.status === 422) return 'Revisa los campos marcados.';
    if (error.status === 404) return 'El cliente ya no está disponible en este taller.';
    return `No se pudo ${action}: ${error.message}`;
  }
}
