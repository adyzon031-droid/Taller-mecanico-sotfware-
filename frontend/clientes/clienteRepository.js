/** Único cliente REST usado por el módulo Vue. */
export class ClienteRepository {
  constructor(baseUrl = window.API_BASE_URL || '') { this.baseUrl = baseUrl; }

  async requestApi(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, {
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

  request(path, options = {}) { return this.requestApi(`/api/clientes${path}`, options); }

  paises() { return this.requestApi('/api/paises'); }
  validarTelefono(region, prefijo, numero) {
    const query = new URLSearchParams({ region, prefijo, numero });
    return this.requestApi(`/api/paises/validar-numero?${query}`);
  }
  ubicacionCp(cp, signal) { return this.requestApi(`/api/ubicacion/cp/${encodeURIComponent(cp)}`, { signal }); }
  ubicacionEstados(signal) { return this.requestApi('/api/ubicacion/estados', { signal }); }
  ubicacionMunicipios(estado, signal) { return this.requestApi(`/api/ubicacion/municipios?${new URLSearchParams({ estado })}`, { signal }); }
  ubicacionColonias(estado, municipio, q = '', signal) { return this.requestApi(`/api/ubicacion/colonias?${new URLSearchParams({ estado, municipio, q })}`, { signal }); }
  buscarCp(estado, municipio, colonia, signal) { return this.requestApi(`/api/ubicacion/buscar?${new URLSearchParams({ estado, municipio, colonia })}`, { signal }); }

  talleres() { return this.requestApi('/api/clientes/talleres'); }
  listar(filtros = {}) { return this.request(`?${new URLSearchParams({ page: 1, page_size: 10, ...filtros })}`); }
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
  cambiarEstado(id, estado, motivo = '') { return this.request(`/${encodeURIComponent(id)}/estado`, { method: 'PATCH', body: JSON.stringify({ estado, motivo }) }); }
  verificarDuplicado(params) { return this.request(`/verificar-duplicado?${new URLSearchParams(params)}`); }
  subirFoto(id, archivo) {
    const form = new FormData(); form.append('foto', archivo);
    return this.request(`/${encodeURIComponent(id)}/foto`, { method: 'POST', body: form });
  }
}
