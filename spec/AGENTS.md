# Repository Guidelines

## Project Structure & Module Organization

The application is a static Vue 3 frontend (loaded as `window.Vue`, JavaScript ES modules, Options API, no build step) plus a Flask API on MariaDB 11. `index.html` defines the screen shell, inline styles and the root app; feature modules live under `frontend/` by domain (`clientes/`, `talleres/`, `empleados/`, `vehiculos/`, `direccion/`). Keep the frontend flow as **view → Facade → Repository → API**.

Backend code is in `backend/`. Each domain generally has a `*_facade.py` for validation/use cases and a `*_repository.py` for SQL access (PyMySQL). HTTP routes are in `backend/app.py`. Versioned, idempotent SQL scripts are in `backend/migrations/`; import helpers are in `backend/scripts/`. Tests are in `backend/tests/`. Runtime uploads belong in `storage/` and are ignored by Git.

TypeScript, Vite and Composition API are **not** used. Pinia 3.0.4 is allowed only for approved state shared by two or more views, with Options API stores; introducing another dependency requires explicit approval.

## Build, Test, and Development Commands

Create and activate a Python virtual environment, then install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/python backend/app.py
```

The API reads `.env` from the repository root and listens on `APP_HOST`/`APP_PORT` (defaults: `127.0.0.1:5000`). Serve the frontend separately:

```bash
python3 -m http.server 4173 --bind 127.0.0.1
.venv/bin/python -m pytest -q backend/tests
```

Run the full test suite before submitting backend or API changes. The frontend has no test runner: verify it manually and never report frontend tests as run unless real output was provided.

## Coding Style & Naming Conventions

Use four spaces in Python, `snake_case` for functions, variables, and modules, and concise Spanish domain names consistent with existing code. JavaScript uses ES modules, `camelCase` methods, and PascalCase component exports such as `DireccionFields`. Pinia stores use Options API (`state`, `getters`, `actions`), JSDoc for state shape, and actions that call facades only. Keep SQL in repositories; do not call API endpoints directly from Vue views. Name migrations with the next zero-padded number, for example `013_nueva_entidad.sql`.

## Testing Guidelines

Use `pytest` and name files `test_*.py`. Cover facade validation, repository behavior through fakes where appropriate, role authorization, and HTTP status codes for new routes. Do not require real credentials or committed upload files for tests.

## Security & Configuration

Never commit `.env`, credentials, tokens, or generated uploads. Copy `.env.example` to `.env` locally and document new configuration keys there with placeholder values. Preserve parameterized SQL, password hashes, session checks, and allowed-origin CORS configuration. Agents must never read, print or ask for `.env` contents.

## Agentes y skills

Cada tarea entra por el orquestador de su capa. Si toca backend y frontend, se ejecuta primero el backend (define el contrato) y después el frontend.

- Backend: `spec/backend/orquestador-backend.md`, que aplica `spec/backend/skill-backend-python.md`.
- Frontend: `spec/frontend/orquestador-frontend.md`, que aplica `spec/frontend/skill-vue.md` y, para fallos, `spec/frontend/skill-depurador.md`.

## Documentación

- Estándar compartido: `spec/agents/documents/documents-estandar.md`
- Backend: `spec/agents/documents/documents-backend.md` (lo invoca la etapa Documentación de `orquestador-backend`)
- Frontend: `spec/agents/documents/documents-frontend.md` (lo invoca la etapa Documentación de `orquestador-frontend`)
- Todo cambio de código termina con la etapa Documentación del orquestador de su capa, después de las pruebas o la verificación.
- Si el cambio toca backend y frontend, se ejecutan ambos orquestadores y cada capa se documenta en su carpeta (`docs/backend/` y `docs/frontend/`).

## Commit & Pull Request Guidelines

Recent history uses short Spanish imperative summaries, for example `Completa CRUD de clientes y navegación por secciones`. Keep commits focused. Pull requests should describe the affected module, migrations, tests run, and include screenshots for visible frontend changes.
