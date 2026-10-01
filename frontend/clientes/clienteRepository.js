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
      error.errors = data.errors || {};
      throw error;
    }
    return data;
  }

  listar(filtros = {}) { return this.request(`?${new URLSearchParams({ page: 1, per_page: 10, ...filtros })}`); }
  consultar(id) { return this.request(`/${encodeURIComponent(id)}`); }
  fotoUrl(id) { return `${this.baseUrl}/api/clientes/${encodeURIComponent(id)}/foto`; }
  crear(cliente, foto = null) {
    if (foto) {
      const form = new FormData();
      form.append('cliente', JSON.stringify(cliente));
      form.append('foto', foto);
      return this.request('', { method: 'POST', body: form });
    }
    return this.request('', { method: 'POST', body: JSON.stringify(cliente) });
  }
  actualizar(id, cliente, foto = null) {
    if (foto) {
      const form = new FormData(); form.append('cliente', JSON.stringify(cliente)); form.append('foto', foto);
      return this.request(`/${encodeURIComponent(id)}`, { method: 'PUT', body: form });
    }
    return this.request(`/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(cliente) });
  }
  eliminar(id) { return this.request(`/${encodeURIComponent(id)}`, { method: 'DELETE' }); }
  verificarDuplicado(params) { return this.request(`/verificar-duplicado?${new URLSearchParams(params)}`); }
  subirFoto(id, archivo) {
    const form = new FormData(); form.append('foto', archivo);
    return this.request(`/${encodeURIComponent(id)}/foto`, { method: 'POST', body: form });
  }
}
