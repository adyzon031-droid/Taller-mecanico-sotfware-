// En desarrollo utiliza Flask local.
// En producción utiliza el mismo dominio donde se sirve el frontend.
const hostsLocales = ["localhost", "127.0.0.1"];

window.API_BASE_URL =
  hostsLocales.includes(window.location.hostname) ||
  window.location.protocol === "file:"
    ? "http://127.0.0.1:5000"
    : "";
