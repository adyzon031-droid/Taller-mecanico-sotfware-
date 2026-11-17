---
name: skill-vue
description: Desarrollo del frontend Vue 3 estático de Torque (JavaScript con módulos ES, Options API, sin build) con el flujo Vista → Store → Facade → Repository → API cuando hay estado compartido aprobado. Usar para vistas, componentes, formularios, validaciones, consumo de la API, estado compartido y transiciones. No usar para backend ni para migrar a TypeScript, Vite o Composition API.
version: 2.1.0
language: es
---

# Frontend Vue 3 estático — Torque

## 1. Rol y activación

Actúa como desarrollador frontend senior. Escribes código simple, consistente con el existente y verificable.

**Activar** para: vistas y componentes, formularios, validaciones, llamadas a la API, transiciones de UI.
**No activar** para: backend, base de datos, estilos globales del `index.html` ni cambios de stack. Esto último se propone como `CR`, no se implementa.

Si la solicitud llega por `orquestador-frontend`, seguir su SPEC. Si es un fallo que hay que diagnosticar, usar `skill-depurador`.

### Stack real (confirmado en el repo)
- Vue 3 cargado como global (`window.Vue`), JavaScript con módulos ES, **Options API** (`createApp({ data() {...} })`).
- Sin build, sin TypeScript, sin `package.json`. Pinia 3.0.4 se usa únicamente para estado compartido aprobado. Se sirve con `python3 -m http.server`.
- Código por dominio en `frontend/` (`clientes/`, `talleres/`, `empleados/`, `vehiculos/`, `direccion/`). Las facades y repositories existentes marcan el patrón.

Antes de escribir, **leer un dominio existente completo** (vista, facade y repository) y copiar su patrón, nombres y estilo.

### Entradas mínimas
Sin ellas se hace una sola pregunta, la más bloqueante:
- Objetivo para el usuario final.
- Contrato de la API (método, ruta, request, response, errores). Viene del backend; no se inventa.
- Campos y reglas del formulario (si aplica).
- Dónde vive la vista afectada (`index.html` o un módulo de `frontend/`).

## 2. SPEC y trazabilidad

- Cada requisito tiene ID (`R1`, `R2`…), un archivo y una verificación.
- No se codifica nada que no esté en la SPEC; lo nuevo se agrega y se reporta.
- Al cerrar, cada requisito queda `hecho`, `pendiente` o `bloqueado`.

```markdown
## SPEC-XXX: <título>
- Objetivo: <una línea>
- Capas: Vista | Facade | Repository | Validación | Transición
- Fuera de alcance: <lo que no se toca>
- Supuestos / TODO: <máx. 3 líneas>

| ID | Requisito | Archivo | Verificación | Estado |
|----|-----------|---------|--------------|--------|
| R1 | <qué debe cumplirse> | frontend/<dominio>/<dominio>Repository.js | <cómo se comprueba> | pendiente |
```

## 3. Arquitectura: Vista → Store → Facade → Repository → API

| Capa | Responsabilidad | No debe |
|------|-----------------|---------|
| Vista / componente | Presentar, capturar eventos, mostrar `loading` y errores | Llamar a `fetch` ni a la API; contener reglas de negocio |
| Store (Pinia) | Mantener solo estado compartido y coordinar facades desde acciones | Llamar a `fetch`; duplicar estado local; guardar secretos o datos personales |
| Facade | Casos de uso: validar, normalizar y coordinar repositories; devolver resultados listos para mostrar | Tocar el DOM; usar `fetch` directo |
| Repository | Único lugar con `fetch`: rutas, método, cuerpo, traducción de errores HTTP | Validar reglas de negocio |
| API (Flask) | Autoridad de validación y permisos | — |

- La validación del cliente mejora la experiencia, no reemplaza la del servidor: mostrar siempre los errores que devuelva la API (`error` y `errors` por campo).
- Si una vista salta una capa y no está en el alcance, reportarla; no corregirla por iniciativa.
- Hoy cada repository implementa su propio transporte. Extraer un cliente común es un `CR`.

### Estado compartido (Pinia)

- Un store por dominio, únicamente para estado compartido por dos o más vistas. El estado de un formulario o vista única permanece en `data()`.
- Usar Options API (`state`, `getters`, `actions`) y documentar la forma de `state` con JSDoc.
- El store nunca llama a `fetch`: sus acciones llaman a una facade. Flujo: **Vista → Store → Facade → Repository → API**.
- Conectar vistas con `mapState` y `mapActions`; no desestructurar el store ni copiar su estado a `data()`.
- No guardar secretos, tokens ni datos personales en el store, ni persistirlo sin una autorización explícita.

## 4. Reglas de desarrollo

- Seguir Options API. Pasar a Composition API es un `CR`.
- Módulos ES con `import`/`export`; `camelCase` en métodos, PascalCase en componentes de varias palabras (`DireccionFields`).
- Nombres de dominio en español, como el código existente.
- No agregar dependencias, CDNs ni librerías (axios, UI kits, validadores, animación). Pinia requiere autorización explícita y versión fija compatible con Vue.
- No inventar endpoints, campos ni propiedades. Si falta el contrato, `// TODO: confirmar contrato`.
- Documentar con JSDoc los parámetros y retornos de facades y repositories (sustituye a los tipos).
- Sin duplicar código; las validaciones reutilizables viven en **una sola utilidad** compartida.
- Sin estado duplicado: lo derivado va en `computed`, no en `data`.
- Sin secretos, URLs de producción ni datos personales en el código.

## 5. Módulos

### Repository (consumo de la API)
- Un archivo por dominio; todas las llamadas de ese dominio viven ahí.
- Devuelve datos o lanza un error con `status` y el cuerpo de error de la API; no decide qué mostrar.
- Manejar red caída, 4xx y 5xx con mensajes claros. Credenciales y base de la URL: copiar de un repository existente.

```js
// Ilustrativo: copiar el patrón real del dominio existente.
export async function listar({ page = 1, pageSize = 20 } = {}) {
  const res = await fetch(`/api/<recurso>?page=${page}&page_size=${pageSize}`)
  const cuerpo = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(cuerpo.error ?? 'Error de red'), { status: res.status, errors: cuerpo.errors })
  return cuerpo
}
```

### Facade (casos de uso y validación)
- Valida antes de llamar al repository y devuelve un resultado uniforme, por ejemplo `{ ok, data, errors }`.
- Traduce los errores del backend (`errors` por campo) al formato que usa el formulario.

### Validaciones
- Funciones puras `(valor) => string | null` (`null` = válido), en la utilidad compartida, nunca inline en el template.
- Mensajes en español, específicos. Validar en `blur` y al enviar, no en cada tecla.
- Reglas de formato del dominio (teléfono de 10 dígitos, correo, CURP, RFC, placa, VIN, CP) deben coincidir con las del backend; ante duda, manda el backend.

### Formularios
- Estado local en `data()`; el componente solo presenta y delega en la facade.
- Deshabilitar el envío mientras `loading` (evita doble envío).
- Errores por campo más un error general del envío.
- Decidir explícitamente qué se conserva o se limpia tras éxito o error.
- Accesibilidad: `label` asociado, `aria-invalid`, `aria-describedby`, `role="alert"` en errores.

### Transiciones (CSS nativo)
- `<Transition>`/`<TransitionGroup>` con clases CSS; animar solo `opacity` y `transform`.
- 150–300 ms, sin bloquear la interacción, respetando `prefers-reduced-motion`.
- Solo donde aporten (errores, modales, listas). Si requieren tocar estilos globales del `index.html`, pedirlo antes.

## 6. Verificación

El frontend no tiene runner de pruebas. Por tanto:
- Cada requisito lleva una **verificación manual** con pasos y resultado esperado (incluido un caso de error de la API).
- Nunca marcar "verificado" sin resultado real aportado por el usuario; usar "No verificado".
- Revisar que no queden `console.log` ni `debugger`, y que ninguna vista llame a la API directamente.

## 7. Formato de salida

- Código completo y listo para pegar, con la ruta de cada archivo; solo los archivos necesarios.
- Supuestos en una línea; pendientes como `TODO`.
- Cerrar con la tabla de trazabilidad actualizada.

## 8. Versionado

| Versión | Cambios |
|---------|---------|
| 2.1.0 | Añade el módulo Estado compartido: Pinia autorizado con Options API, JSDoc, un store por dominio, sin duplicar estado ni llamar a `fetch`. Actualiza el flujo para incluir Store cuando aplique. |
| 2.0.0 | Reescrita para el stack real: JavaScript estático, Vue 3 global y Options API, flujo Vista → Facade → Repository → API. Se eliminan TypeScript, Pinia, `src/`, `apiClient.ts`, `useApi` y Vite. Verificación manual explícita. |
| 1.1.0 | Versión anterior (TypeScript + Pinia + Vite), no aplicable a este repo. |
