import { DireccionRepository } from './direccionRepository.js';

export function opcionesColoniasUnicas(rows = []) {
  const seen = new Set();
  return rows.filter(row => {
    const key = String(row.colonia || '').trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es-MX');
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  }).sort((a, b) => a.colonia.localeCompare(b.colonia, 'es-MX'));
}

export class DireccionFacade {
  constructor(repository = new DireccionRepository()) { this.repository = repository; }
  estados(signal) { return this.repository.estados(signal); }
  municipios(estado, signal) { return this.repository.municipios(estado, signal); }
  colonias(estado, municipio, q = '', signal) { return this.repository.colonias(estado, municipio, q, signal); }
  codigoPostal(cp, signal) { return this.repository.codigoPostal(cp, signal); }
  codigosPostales(estado, municipio, colonia, signal) { return this.repository.codigosPostales(estado, municipio, colonia, signal); }
  async validar(address, { manual = false, signal } = {}) {
    if (manual) return true;
    if (!address?.estado || !address?.municipio || !address?.colonia || !/^\d{5}$/.test(String(address?.codigo_postal || ''))) return false;
    try {
      const result = await this.codigoPostal(address.codigo_postal, signal);
      return result.estados.includes(address.estado) && result.colonias.some(row => row.estado === address.estado && row.municipio === address.municipio && row.colonia === address.colonia);
    } catch (error) { if (error.name === 'AbortError') throw error; return error.status === 503; }
  }
}
