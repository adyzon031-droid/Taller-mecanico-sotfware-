import { AuthRepository } from './authRepository.js';

/** Coordina autenticación, sesión y notificaciones del login. */
export class AuthFacade {
  constructor(repository = new AuthRepository()) { this.repository = repository; }
  async login(email, password) {
    if (!email || !password) throw new Error('Ingresa correo y contraseña.');
    return this.repository.login(email.trim(), password);
  }
  logout() { return this.repository.logout(); }
  sesion() { return this.repository.sesion(); }
}
