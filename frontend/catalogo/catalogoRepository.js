/** Único cliente HTTP del catálogo de marcas y modelos. */
export class CatalogoRepository {
  constructor(baseUrl = window.API_BASE_URL || '') { this.baseUrl = baseUrl; }

  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || `Error HTTP ${response.status}`);
      error.status = response.status;
      error.errors = data.errors || {};
      throw error;
    }
    return data;
  }

  get(path, signal) { return this.request(path, { signal }); }
  post(path, body) { return this.request(path, { method: 'POST', body: JSON.stringify(body) }); }
  put(path, body) { return this.request(path, { method: 'PUT', body: JSON.stringify(body) }); }
  patch(path) { return this.request(path, { method: 'PATCH' }); }

  marcas(params = {}, signal) { return this.get(`/api/marcas?${new URLSearchParams(params)}`, signal); }
  modelos(params = {}, signal) { return this.get(`/api/modelos?${new URLSearchParams(params)}`, signal); }
  opcionesMarcas(q = '', signal) { return this.get(`/api/marcas/opciones${q ? `?q=${encodeURIComponent(q)}` : ''}`, signal); }
  opcionesModelos(brandId, q = '', signal) { return this.get(`/api/marcas/${encodeURIComponent(brandId)}/modelos/opciones${q ? `?q=${encodeURIComponent(q)}` : ''}`, signal); }
  buscar(q, brandId = '', signal) {
    const params = new URLSearchParams({ q });
    if (brandId) params.set('marca_id', brandId);
    return this.get(`/api/catalogo-vehiculos/buscar?${params}`, signal);
  }
  resolverPendiente(data) { return this.post('/api/catalogo-vehiculos/pendiente', data); }
  crearMarca(data) { return this.post('/api/marcas', data); }
  editarMarca(id, data) { return this.put(`/api/marcas/${encodeURIComponent(id)}`, data); }
  crearModelo(data) { return this.post('/api/modelos', data); }
  editarModelo(id, data) { return this.put(`/api/modelos/${encodeURIComponent(id)}`, data); }
  estado(tipo, id, activo) { return this.patch(`/api/${tipo}/${encodeURIComponent(id)}/${activo ? 'reactivar' : 'desactivar'}`); }
}
