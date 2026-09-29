/** Único cliente REST usado por el módulo Vue. */
export class ClienteRepository {
  constructor(baseUrl = window.API_BASE_URL || '') { this.baseUrl = baseUrl; }

  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}/api/clientes${path}`, {
      credentials: 'include',
      ...options,
      headers: options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || `Error HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  listar(filtros = {}) { return this.request(`?${new URLSearchParams(filtros)}`); }
  consultar(id) { return this.request(`/${encodeURIComponent(id)}`); }
  crear(cliente) { return this.request('', { method: 'POST', body: JSON.stringify(cliente) }); }
  actualizar(id, cliente) { return this.request(`/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(cliente) }); }
  verificarDuplicado(params) { return this.request(`/verificar-duplicado?${new URLSearchParams(params)}`); }
  subirFoto(id, archivo) {
    const form = new FormData(); form.append('foto', archivo);
    return this.request(`/${encodeURIComponent(id)}/foto`, { method: 'POST', body: form });
  }
}
