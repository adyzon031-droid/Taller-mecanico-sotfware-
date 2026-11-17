/** Transporte REST del catálogo de estatus, con cookie de sesión. */
export class EstatusRepository {
  constructor(baseUrl = window.API_BASE_URL || '') { this.baseUrl = baseUrl; }
  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(data.error || `HTTP ${response.status}`); error.status = response.status; error.errors = data.errors || {}; throw error; }
    return data;
  }
  list(params = {}) { return this.request(`/api/estatus?${new URLSearchParams(params)}`); }
  options() { return this.request('/api/estatus/opciones'); }
  get(id) { return this.request(`/api/estatus/${encodeURIComponent(id)}`); }
  save(id, data) { return this.request(id ? `/api/estatus/${encodeURIComponent(id)}` : '/api/estatus', { method: id ? 'PUT' : 'POST', body: JSON.stringify(data) }); }
  activate(id, active) { return this.request(`/api/estatus/${encodeURIComponent(id)}/${active ? 'reactivar' : 'desactivar'}`, { method: 'PATCH' }); }
}
