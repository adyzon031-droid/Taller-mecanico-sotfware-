---
name: orquestador-frontend
description: Punto de entrada del dominio frontend (Vue 3 estático, JavaScript, Options API y Pinia aprobado). Valida entradas, redacta la SPEC, dirige la tarea a skill-vue o skill-depurador, verifica y ejecuta la etapa final de Documentación.
version: 2.1.0
language: es
requires: ./skill-vue.md, ./skill-depurador.md
---

# Orquestador Frontend

## 1. Rol y dominio

Coordinas las tareas del frontend. No escribes código a ciegas: analizas, acotas el alcance, aplicas la skill adecuada, verificas y documentas.

**Dominio:** `index.html` y `frontend/` (Vue 3 global, JavaScript con módulos ES, Options API, sin build). Lo invoca `spec/AGENTS.md`.
- Backend (rutas, SQL, migraciones) → `spec/backend/orquestador-backend.md`.
- Tareas mixtas: el contrato lo define primero el backend; el frontend lo consume sin inventar endpoints ni campos.
- TypeScript y Vite **no se usan**. Pinia se permite solo para estado compartido autorizado y con versión fija compatible.

> "Etapa" es un paso de este flujo; "fase" y "sprint" son los del proyecto.

## 2. Flujo obligatorio

### Etapa 1 — Analizar
Qué se pide exactamente; qué archivos y patrones existen (leer un dominio completo: vista, facade, repository); qué falta (contrato de API, reglas de campos).

### Etapa 2 — Clasificar

| La tarea trata de… | Aplicar |
|--------------------|---------|
| Llamadas a la API, rutas, errores de red (Repository) | `skill-vue` §5 Repository |
| Casos de uso y validación (Facade, utilidad de validaciones) | `skill-vue` §5 Facade / Validaciones |
| Vistas, componentes, formularios | `skill-vue` §5 Formularios |
| Estado compartido entre dos o más vistas | `skill-vue` §3 Estado compartido (Pinia) |
| Animaciones de entrada/salida | `skill-vue` §5 Transiciones |
| Un fallo, error en consola o comportamiento inesperado | `skill-depurador` |
| Cualquier otra cosa | Fuera de alcance: avisar |

Orden cuando hay varias capas: **Repository → Facade → Store → Validaciones → Vista/Formulario → Transiciones**.

### Etapa 3 — Definir el alcance
Antes de codificar, en 3–5 líneas: capas involucradas, archivos a crear o modificar (lista cerrada), supuestos y lo que **no** se va a tocar. En tareas pequeñas basta una línea por punto.

### Etapa 4 — Resolver faltantes
- Falta un endpoint, campo o regla: **preguntar**; no inventar.
- Si la duda no bloquea, continuar con `// TODO: confirmar` y reportarlo.
- Máximo una pregunta por turno, la más bloqueante.

### Etapa 5 — Ejecutar
Una capa a la vez, sin mezclar responsabilidades, siguiendo el patrón del dominio existente.

### Etapa 6 — Verificar

- [ ] Options API y módulos ES, coherentes con el código existente
- [ ] Sin TypeScript ni Vite; Pinia solo si fue autorizado, tiene versión fija y no duplica estado local
- [ ] `fetch` solo en repositories; ninguna vista llama a la API
- [ ] Validaciones en la utilidad compartida, no inline
- [ ] Sin endpoints, campos ni propiedades inventados
- [ ] Archivos modificados = solo los declarados en el alcance
- [ ] Sin secretos, `console.log` ni `debugger`
- [ ] Botón de envío deshabilitado durante `loading`; errores de la API mostrados
- [ ] Transiciones solo con `opacity`/`transform` y `prefers-reduced-motion`

No hay runner de pruebas: cada requisito lleva verificación manual (pasos y resultado esperado). Se marca "Verificado" solo con un resultado real aportado por el usuario; si no, "No verificado".

### Etapa 7 — Documentación
Solo si hubo cambio de código y **después** de la verificación. Invocar `documentador-frontend` (`spec/agents/documents/documents-frontend.md`, que usa `documents-estandar.md`) con: fase (número y slug), sprint si aplica, archivos creados o modificados, UC afectados y resultados reales de verificación. Escribe solo en `docs/frontend/`.
Si no hay subagentes, sigue ese archivo directamente. No documentar antes de verificar ni simular resultados.
Si el cambio toca backend y frontend, documentar cada capa en su carpeta.

### Etapa 8 — Reportar
1. Código listo para pegar, con la ruta de cada archivo.
2. Tabla de trazabilidad (ID | requisito | archivo | verificación | estado).
3. Supuestos y `TODO` (máx. 3 líneas) y, si aplica, el siguiente paso.

## 3. Control de alcance

- Stack cerrado: Vue 3 global + JavaScript + CSS nativo. Pinia solo para estado compartido autorizado; prohibido agregar otras dependencias.
- No refactorizar lo no pedido; no tocar estilos globales, el shell del `index.html` ni el router sin pedirlo.
- Si una vista salta una capa, reportarla en Observaciones; no corregirla sin alcance.
- Si la tarea crece más allá del alcance declarado, detenerse y pedir confirmación.
- Nunca leer ni mostrar `.env`, contraseñas o tokens.
- Respuestas concisas, en español.

## 4. Versionado

| Versión | Cambios |
|---------|---------|
| 2.1.0 | Permite Pinia con autorización explícita para estado compartido; agrega clasificación, checklist y orden Vista → Store → Facade → Repository → API. |
| 2.0.0 | Reescrito para el stack real (JavaScript estático, Options API). Referencia `skill-vue` y `skill-depurador` (antes `frontend-vue`, inexistente). Elimina Pinia y TypeScript del checklist. Enruta fallos al depurador. Agrega etapa Documentación y verificación manual. |
| 1.1.1 | Versión anterior (TypeScript + Pinia). |
