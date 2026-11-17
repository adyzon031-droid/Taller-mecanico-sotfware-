import { VehiculoRepository } from './vehiculoRepository.js';
/** Normaliza campos del vehículo; el backend vuelve a validar cada regla. */
export class VehiculoFacade {
  constructor(repository = new VehiculoRepository()) { this.repository = repository; }
  normalizarPlaca(value) { return String(value || '').replace(/[-\s]/g, '').toUpperCase(); }
  validar(data) {
    const errors = {}, placa = this.normalizarPlaca(data.placa);
    if (!/^[A-Z0-9]{5,8}$/.test(placa)) errors.placa = 'Usa de 5 a 8 letras o números.';
    if (!data.marca) errors.marca = 'Selecciona o escribe una marca.';
    const year = Number(data.anio), now = new Date().getFullYear();
    if (!Number.isInteger(year) || year < 1900 || year > now + 1) errors.anio = `Usa un año entre 1900 y ${now + 1}.`;
    if (!data.fecha_ingreso) errors.fecha_ingreso = 'La fecha de ingreso es obligatoria.';
    return errors;
  }
  listar(params) { return this.repository.list(params); }
  registrar(data) { const errors = this.validar(data); if (Object.keys(errors).length) throw Object.assign(new Error('Revisa los campos indicados.'), { status: 422, errors }); return this.repository.save({ ...data, placa: this.normalizarPlaca(data.placa) }); }
  actualizar(id, data) { const errors = this.validar(data); if (Object.keys(errors).length) throw Object.assign(new Error('Revisa los campos indicados.'), { status: 422, errors }); return this.repository.update(id, { ...data, placa: this.normalizarPlaca(data.placa) }); }
  validarActivacion(data) {
    const errors = this.validar(data);
    if (!String(data.modelo || '').trim()) errors.modelo = 'El modelo es obligatorio para activar el vehículo.';
    if (!String(data.version || '').trim()) errors.version = 'La versión es obligatoria para activar el vehículo.';
    if (!String(data.numero_serie || '').trim()) errors.numero_serie = 'El VIN es obligatorio para activar el vehículo.';
    if (data.kilometraje === '' || data.kilometraje === null || data.kilometraje === undefined) errors.kilometraje = 'El kilometraje es obligatorio para activar el vehículo.';
    return errors;
  }
  activar(id, data) { const errors = this.validarActivacion(data); if (Object.keys(errors).length) throw Object.assign(new Error('Completa la ficha antes de activar el vehículo.'), { status: 422, errors }); return this.repository.activate(id, { ...data, placa: this.normalizarPlaca(data.placa) }); }
  desactivar(id, motivo) {
    const clean = String(motivo || '').trim();
    const errors = {};
    if (clean.length < 3 || clean.length > 500) errors.motivo = 'Indica un motivo de 3 a 500 caracteres.';
    if (Object.keys(errors).length) throw Object.assign(new Error('Revisa los campos indicados.'), { status: 422, errors });
    return this.repository.deactivate(id, { confirmado: true, motivo: clean });
  }
  verificarPlaca(plate, exclude) { return this.repository.verifyPlate(this.normalizarPlaca(plate), exclude); }
  porCliente(id, params) { return this.repository.byClient(id, params); }
  relaciones(id, includeHistory = false) { return this.repository.relations(id, includeHistory); }
  asociar(id, data) { return this.repository.associate(id, data); }
  cambiarPropietario(id, data) {
    const errors = {};
    if (!data.cliente_nuevo_id) errors.cliente_nuevo_id = 'Selecciona un cliente.';
    if (!data.fecha_efectiva) errors.fecha_efectiva = 'Selecciona la fecha efectiva.';
    if (String(data.motivo || '').trim().length < 10) errors.motivo = 'Indica un motivo de al menos 10 caracteres.';
    if (Object.keys(errors).length) throw Object.assign(new Error('Revisa los campos indicados.'), { status: 422, errors });
    return this.repository.changeOwner(id, data);
  }
  eliminar(id) { return this.repository.remove(id); }
  restaurar(id) { return this.repository.restore(id); }
}
