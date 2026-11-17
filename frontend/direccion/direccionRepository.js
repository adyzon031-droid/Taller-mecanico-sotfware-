/** Único acceso HTTP para el catálogo de ubicación. */
export class DireccionRepository {
  constructor(baseUrl = window.API_BASE_URL || '') { this.baseUrl = baseUrl; }

  async request(path, signal) {
    const response = await fetch(`${this.baseUrl}${path}`, { credentials: 'include', signal });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || `Error HTTP ${response.status}`);
      error.status = response.status;
      error.errors = data.errors || {};
      throw error;
    }
    return data;
  }

  estados(signal) { return this.request('/api/ubicacion/estados', signal); }
  municipios(estado, signal) {
    return this.request(`/api/ubicacion/municipios?${new URLSearchParams({ estado })}`, signal);
  }
  colonias(estado, municipio, query = '', signal) {
    return this.request(`/api/ubicacion/colonias?${new URLSearchParams({ estado, municipio, q: query })}`, signal);
  }
  codigoPostal(cp, signal) {
    return this.request(`/api/ubicacion/cp/${encodeURIComponent(cp)}`, signal);
  }
  codigosPostales(estado, municipio, colonia, signal) {
    return this.request(`/api/ubicacion/buscar?${new URLSearchParams({ estado, municipio, colonia })}`, signal);
  }
}
