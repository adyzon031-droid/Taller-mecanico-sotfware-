import { AuthFacade } from './authFacade.js';

const { defineStore } = window.Pinia;
const authFacade = new AuthFacade();

/**
 * @typedef {Object} EstadoSesion
 * @property {boolean} authenticated Indica si el backend reconoce la sesión actual.
 * @property {string} rol Rol autorizado por el backend para la sesión actual.
 * @property {number|null} taller_id Taller activo autorizado por el backend.
 * @property {boolean} cargada Indica que la comprobación inicial de sesión terminó.
 */

/** Store del contexto mínimo de sesión compartido entre las vistas. */
export const useSesionStore = defineStore('sesion', {
  /** @returns {EstadoSesion} */
  state: () => ({
    authenticated: false,
    rol: '',
    taller_id: null,
    cargada: false,
  }),

  getters: {
    tieneSesion: (state) => state.authenticated,
  },

  actions: {
    aplicarUsuario(usuario) {
      this.authenticated = true;
      this.rol = String(usuario?.rol || '');
      this.taller_id = usuario?.taller_id ?? null;
    },

    limpiar() {
      this.authenticated = false;
      this.rol = '';
      this.taller_id = null;
    },

    async rehidratarSesion() {
      try {
        const resultado = await authFacade.sesion();
        this.aplicarUsuario(resultado.usuario);
        return resultado.usuario;
      } catch (error) {
        if (error.status === 401) this.limpiar();
        throw error;
      } finally {
        this.cargada = true;
      }
    },

    async iniciarSesion(email, password) {
      const resultado = await authFacade.login(email, password);
      this.aplicarUsuario(resultado.usuario);
      this.cargada = true;
      return resultado.usuario;
    },

    async cerrarSesion() {
      try {
        return await authFacade.logout();
      } finally {
        this.limpiar();
        this.cargada = true;
      }
    },
  },
});
