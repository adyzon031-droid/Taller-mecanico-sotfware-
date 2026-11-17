/** Único transporte REST de vehículos. */
export class VehiculoRepository {
  constructor(baseUrl = window.API_BASE_URL || '') { this.baseUrl = baseUrl; }
  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(data.error || `HTTP ${response.status}`); error.status = response.status; error.errors = data.errors || {}; throw error; }
    return data;
  }
  list(params = {}) { return this.request(`/api/vehiculos?${new URLSearchParams(params)}`); }
  save(data) { return this.request('/api/vehiculos', { method: 'POST', body: JSON.stringify(data) }); }
  get(id) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}`); }
  update(id, data) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(data) }); }
  activate(id, data) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}/activar`, { method: 'PATCH', body: JSON.stringify(data) }); }
  deactivate(id, data) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}/desactivar`, { method: 'PATCH', body: JSON.stringify(data) }); }
  verifyPlate(plate, excludeId = '') { const p = new URLSearchParams({ placa: plate }); if (excludeId) p.set('excluir_id', excludeId); return this.request(`/api/vehiculos/verificar-placa?${p}`); }
  byClient(id, params = {}) { return this.request(`/api/clientes/${encodeURIComponent(id)}/vehiculos?${new URLSearchParams(params)}`); }
  relations(id, includeHistory = false) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}/relaciones${includeHistory ? '?incluir_historicos=1' : ''}`); }
  associate(id, data) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}/relaciones`, { method: 'POST', body: JSON.stringify(data) }); }
  changeOwner(id, data) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}/cambiar-propietario`, { method: 'POST', body: JSON.stringify(data) }); }
  remove(id) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}/eliminar`, { method: 'PATCH' }); }
  restore(id) { return this.request(`/api/vehiculos/${encodeURIComponent(id)}/restaurar`, { method: 'PATCH' }); }
}
