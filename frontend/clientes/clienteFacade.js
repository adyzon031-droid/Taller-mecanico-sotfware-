import { ClienteRepository } from './clienteRepository.js';

/** Punto de acceso de la vista; traduce resultados y notifica el estado. */
export class ClienteFacade {
  constructor(repository = new ClienteRepository(), notificar = () => {}) {
    this.repository = repository;
    this.notificar = notificar;
  }

  validar(cliente) {
    const requeridos = ['nombre_completo','edad','fecha_nacimiento','telefono_personal','telefono_trabajo','email','calle','colonia','municipio','estado','codigo_postal'];
    if (requeridos.some(key => !String(cliente[key] ?? '').trim())) throw new Error('Completa todos los campos requeridos.');
    const email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const telefono = /^\+?[0-9 ()-]{7,20}$/;
    if (!email.test(cliente.email) || (cliente.email_trabajo && !email.test(cliente.email_trabajo))) throw new Error('Revisa el formato del correo.');
    if (![cliente.telefono_personal, cliente.telefono_trabajo].every(value => telefono.test(value))) throw new Error('Revisa el formato de los teléfonos.');
    if (!/^\d{5}$/.test(cliente.codigo_postal)) throw new Error('El código postal debe tener cinco dígitos.');
    const fecha = new Date(`${cliente.fecha_nacimiento}T00:00:00`);
    const hoy = new Date();
    let edad = hoy.getFullYear() - fecha.getFullYear();
    if (hoy.getMonth() < fecha.getMonth() || (hoy.getMonth() === fecha.getMonth() && hoy.getDate() < fecha.getDate())) edad--;
    if (Number.isNaN(fecha.getTime()) || fecha > hoy || edad !== Number(cliente.edad)) throw new Error('La edad debe coincidir con la fecha de nacimiento.');
    if (cliente.foto && (!['image/jpeg','image/png','image/webp'].includes(cliente.foto.type) || cliente.foto.size > 15 * 1024 * 1024)) throw new Error('La foto debe ser JPG, PNG o WEBP y no superar 15 MB.');
  }

  async registrar(cliente) {
    try {
      this.validar(cliente);
      const duplicate = await this.repository.verificarDuplicado({
        email: cliente.email, telefono_personal: cliente.telefono_personal,
        nombre_completo: cliente.nombre_completo, fecha_nacimiento: cliente.fecha_nacimiento,
      });
      if (duplicate.duplicado) throw Object.assign(new Error('Ya existe un cliente con esos datos.'), { status: 409 });
      const { foto, ...payload } = cliente;
      const result = await this.repository.crear(payload);
      if (foto) await this.repository.subirFoto(result.id, foto);
      this.notificar('Cliente registrado correctamente.', 'success');
      return result;
    } catch (error) {
      this.notificar(error.status === 409 ? 'Registro rechazado: cliente duplicado.' : `No se pudo registrar: ${error.message}`, 'error');
      throw error;
    }
  }

  async listar(filtros) { return this.repository.listar(filtros); }
}
