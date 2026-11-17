import { CatalogoRepository } from './catalogoRepository.js';

/** Coordina validación ligera y operaciones del catálogo. El backend valida de nuevo. */
export class CatalogoFacade {
  constructor(repository = new CatalogoRepository()) { this.repository = repository; }

  normalizarNombre(value) {
    const acronyms = new Set(['BMW', 'GMC', 'RAM', 'SEAT']);
    return String(value || '').trim().replace(/\s+/g, ' ').split(' ').filter(Boolean).map(word =>
      word.split('-').map(part => acronyms.has(part.toUpperCase()) ? part.toUpperCase() : part[0].toUpperCase() + part.slice(1).toLowerCase()).join('-'),
    ).join(' ');
  }

  validarNombre(value, max) {
    const name = this.normalizarNombre(value);
    if (!name) return { nombre: 'Este campo es obligatorio.' };
    if (name.length > max) return { nombre: `Máximo ${max} caracteres.` };
    if (!/^[\wÀ-ÿ][\wÀ-ÿ .&'’()/+-]*$/u.test(name)) return { nombre: 'Usa letras, números y separadores habituales.' };
    return {};
  }

  listarMarcas(params) { return this.repository.marcas(params); }
  listarModelos(params) { return this.repository.modelos(params); }
  opcionesMarcas(q, signal) { return this.repository.opcionesMarcas(q, signal); }
  opcionesModelos(id, q, signal) { return this.repository.opcionesModelos(id, q, signal); }
  buscar(q, id, signal) { return this.repository.buscar(q, id, signal); }
  resolverPendiente(data) { return this.repository.resolverPendiente(data); }
  guardarMarca(id, nombre) { return id ? this.repository.editarMarca(id, { nombre }) : this.repository.crearMarca({ nombre }); }
  guardarModelo(id, marca_id, nombre) { return id ? this.repository.editarModelo(id, { marca_id, nombre }) : this.repository.crearModelo({ marca_id, nombre }); }
  estado(tipo, id, activo) { return this.repository.estado(tipo, id, activo); }
}
