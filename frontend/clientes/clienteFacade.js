import { ClienteRepository } from './clienteRepository.js';

/** Punto de acceso de la vista; traduce resultados y notifica el estado. */
export class ClienteFacade {
  constructor(repository = new ClienteRepository(), notificar = () => {}) {
    this.repository = repository;
    this.notificar = notificar;
  }

  errores(cliente) {
    const requeridos = ['nombre_completo','edad','fecha_nacimiento','telefono_personal','telefono_trabajo','email','calle','colonia','municipio','estado','codigo_postal'];
    const errores = {};
    for (const key of requeridos) if (!String(cliente[key] ?? '').trim()) errores[key] = 'Este campo es obligatorio.';
    const email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const telefono = /^\+?[0-9 ()-]{7,20}$/;
    if (cliente.email && !email.test(cliente.email)) errores.email = 'Escribe un correo válido.';
    if (cliente.email_trabajo && !email.test(cliente.email_trabajo)) errores.email_trabajo = 'Escribe un correo válido.';
    if (cliente.telefono_personal && !telefono.test(cliente.telefono_personal)) errores.telefono_personal = 'Formato de teléfono inválido.';
    if (cliente.telefono_trabajo && !telefono.test(cliente.telefono_trabajo)) errores.telefono_trabajo = 'Formato de teléfono inválido.';
    if (cliente.codigo_postal && !/^\d{5}$/.test(cliente.codigo_postal)) errores.codigo_postal = 'Usa cinco dígitos.';
    if (cliente.fecha_nacimiento && cliente.edad !== '' && cliente.edad != null) {
      const fecha = new Date(`${cliente.fecha_nacimiento}T00:00:00`);
      const hoy = new Date();
      let edad = hoy.getFullYear() - fecha.getFullYear();
      if (hoy.getMonth() < fecha.getMonth() || (hoy.getMonth() === fecha.getMonth() && hoy.getDate() < fecha.getDate())) edad--;
      if (Number.isNaN(fecha.getTime()) || fecha > hoy || edad !== Number(cliente.edad)) errores.edad = 'No coincide con la fecha de nacimiento.';
    }
    if (cliente.foto) {
      const extensionValida = /\.(jpg|jpeg|png|webp)$/i.test(cliente.foto.name);
      const tipoValido = ['image/jpeg','image/png','image/webp'].includes(cliente.foto.type);
      if (!extensionValida || !tipoValido) errores.foto = 'Formato inválido. Usa JPG, JPEG, PNG o WEBP.';
      else if (cliente.foto.size > 15 * 1024 * 1024) errores.foto = 'El máximo permitido es 15 MB.';
    }
    return errores;
  }

  validar(cliente) {
    const errores = this.errores(cliente);
    if (Object.keys(errores).length) throw Object.assign(new Error(Object.values(errores)[0]), { fieldErrors: errores });
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
      const result = await this.repository.crear(payload, foto);
      this.notificar('Cliente registrado correctamente.', 'success');
      return result;
    } catch (error) {
      this.notificar(error.status === 409 ? 'Registro rechazado: cliente duplicado.' : `No se pudo registrar: ${error.message}`, 'error');
      throw error;
    }
  }

  async listar(filtros) { return this.repository.listar(filtros); }
}
