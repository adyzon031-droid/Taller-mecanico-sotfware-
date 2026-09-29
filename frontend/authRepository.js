/** Único cliente REST para autenticación de sesión. */
export class AuthRepository {
  constructor(baseUrl = window.API_BASE_URL || '') { this.baseUrl = baseUrl; }

  async request(path, body) {
    const response = await fetch(`${this.baseUrl}/api/auth/${path}`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Error HTTP ${response.status}`);
    return data;
  }
  login(email, password) { return this.request('login', { email, password }); }
  logout() { return this.request('logout'); }
  sesion() { return this.request('sesion'); }
}
