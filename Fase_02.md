# Fase 02 · Registro de clientes

## Análisis previo (revisión del repositorio)

1. El repositorio tiene `index.html` con login Vue demostrativo; acepta cualquier correo/contraseña y no solicita sesión a un servicio.
2. No hay backend previo, token, sesión de servidor, guards Vue, usuarios, talleres, notificaciones funcionales ni esquema MySQL.
3. El `.env.example` de fase 1 ya propone MySQL; no hay `.env` real y `.gitignore` excluye `.env`.
4. Se conserva el login visual existente; el registro nuevo usa una vista de formulario dentro del panel y no altera su presentación.
5. La API exige sesión firmada con `usuario_id`, `rol` y `taller_id`; el login actual no crea esa sesión, por lo que el flujo integrado queda **PENDIENTE**.

## Arquitectura implementada

Flujo: **Vista Vue → `ClienteFacade` frontend → `ClienteRepository` frontend → API REST Flask → `ClienteFacade` backend → `ClienteRepository` backend → MySQL**. El guard backend valida sesión, rol y taller; la capa Repository restringe todas las lecturas/cambios al `taller_id` de sesión. La fotografía se guarda en `storage/clientes/` y en MySQL se almacena su ruta.

El diagrama HTML/SVG está en [docs/diagramas/fase-02-componentes-registro-clientes.html](docs/diagramas/fase-02-componentes-registro-clientes.html) y [docs/diagramas/fase-02-componentes-registro-clientes.svg](docs/diagramas/fase-02-componentes-registro-clientes.svg). **Archify no se utilizó:** falló su instalación porque `npx` no está instalado. El dibujo manual se limita a las capas/controles presentes en el código; señala como pendiente la sesión que el login aún no genera.

## Módulos y actividades

| Actividad | Estado (Realizada/Pendiente) | Observaciones |
|---|---|---|
| Formulario Vue de datos del cliente | Realizada | Campos del requisito, edad derivada de nacimiento, aviso visible y validaciones en el facade. |
| Facade y Repository frontend | Realizada | La vista invoca la facade; el repository usa `fetch` para la API con credenciales de sesión. |
| API REST para clientes | Realizada | Rutas de alta, listado, consulta, actualización, carga de foto y verificación de duplicados. |
| Validación backend y duplicados | Realizada | Valida correos, teléfonos, edad/fecha, CP, taller y duplicidad; duplicados SQL retornan 409. |
| Permiso por rol en backend | Realizada | Acepta administrador/admin, secretaria y recepcionista. Depende de una sesión autenticada. |
| Aislamiento multi-taller | Realizada | API obtiene `taller_id` de la sesión y filtra por taller; el listado no acepta el taller enviado por el navegador. |
| Tablas `empresas`, `talleres`, `clientes` | Realizada | Script versionado. Faltan filas iniciales de empresa/taller y el sistema de usuarios del proyecto. |
| Conexión al MySQL local | Realizada (código) | PyMySQL lee variables de entorno; conexión real y persistencia no verificadas porque no hay `.env` ni backend previo. |
| Guard de ruta del frontend / sesión de login | Pendiente | El login actual solo cambia la vista; no existe identidad confiable ni guard de rutas.
| Alta real con notificación de éxito | Pendiente | Implementada la interfaz/API, pero la API contestará 401 hasta conectar el login y crear la sesión con usuario/rol/taller.
| Transacción conjunta cliente + fotografía | Pendiente | Cliente y foto usan operaciones separadas. Foto actualiza ruta en transacción SQL y borra el archivo si falla; falta una transacción/compensación atómica del flujo completo.
| Prueba contra MySQL local (alta y duplicado) | Pendiente | No se ejecutó: no hay runtime previo ni `.env` configurado; no se usaron credenciales existentes.
| Publicación/commit/push | Pendiente | Requiere revisar y publicar en GitHub tras verificar la sesión y base locales.

## Código: funciones, métodos y endpoints

### Frontend

| Nombre | Capa | Propósito | Parámetros → retorno |
|---|---|---|---|
| `ClienteFacade.validar(cliente)` | Facade Vue | Comprueba requeridos, correo, teléfonos, fecha/edad, CP y foto ≤15 MB. | cliente → `undefined`; lanza `Error` si inválido. |
| `ClienteFacade.registrar(cliente)` | Facade Vue | Valida, consulta duplicado, crea cliente, carga foto si se seleccionó y emite notificación. | cliente → Promise del registro; lanza error HTTP/validación. |
| `ClienteFacade.listar(filtros)` | Facade Vue | Solicita lista filtrada al repository. | filtros → Promise de respuesta. |
| `ClienteRepository.request(path, options)` | Repository Vue | Envía HTTP JSON o multipart con cookie de sesión; transforma respuestas no 2xx en error. | ruta/opciones → Promise JSON. |
| `listar`, `consultar`, `crear`, `actualizar`, `verificarDuplicado`, `subirFoto` | Repository Vue | Envolturas HTTP de los endpoints homónimos. | filtro/id/datos/archivo → Promise JSON. |
| `abrirClientes`, `limpiarCliente`, `calcularEdad`, `seleccionarFoto`, `registrarCliente` | Vista Vue | Abre formulario, limpia campos, calcula edad, valida selección de imagen y conecta la vista a la facade. | evento/campo → actualiza estado Vue; `registrarCliente` retorna Promise interna. |

### Backend

| Método / ruta | Controlador y propósito | Retorno |
|---|---|---|
| `POST /api/clientes` | `crear_cliente`: JSON validado; agrega `taller_id`/`creado_por` desde sesión. | `201` con id; `401/403` sesión/rol; `409` duplicado; `422` inválido. |
| `GET /api/clientes` | `listar_clientes`: consulta por nombre, email o teléfono dentro del taller de sesión. | `200` JSON con clientes. |
| `GET /api/clientes/{id}` | `consultar_cliente`: consulta por id y taller activo. | `200` o `404`. |
| `PUT /api/clientes/{id}` | `actualizar_cliente`: valida y actualiza el registro dentro del taller activo. | `200`, `404`, `409` o `422`. |
| `POST /api/clientes/{id}/foto` | `subir_foto`: limita 15 MB, valida extensión/firma, almacena archivo y actualiza `foto_ruta`. | `201`, `404` o `422`. |
| `GET /api/clientes/verificar-duplicado` | `verificar_duplicado`: revisa email/teléfono/nombre y nacimiento en el taller activo. | `200 {duplicado: boolean}`. |
| `requiere_rol(view)` | Decorador de autorización: exige sesión con `usuario_id`, rol permitido y `taller_id`. | Deja pasar o responde `401/403`. |
| `validar(datos)` | Facade backend: valida campos/formato/edad. | Diccionario normalizado o `ClienteError` `422`. |
| `ClienteFacade.crear/listar/obtener/actualizar` | Reglas negocio: valida, detecta duplicados y delega acceso a datos. | Id, lista, fila, booleano o excepción. |
| `ClienteRepository.crear/listar/obtener/actualizar/duplicado/guardar_foto_y_actualizar` | Única capa que ejecuta SQL con placeholders parametrizados; cada cambio abre transacción y hace commit/rollback. | Id, filas, booleano o error DB. |
| `connect()` | Infraestructura MySQL; configura PyMySQL con entorno. No ejecuta consultas de negocio. | Conexión MySQL con `autocommit=False`. |

Archivos nuevos/modificados: `backend/app.py`, `backend/cliente_facade.py`, `backend/cliente_repository.py`, `backend/db.py`, `backend/requirements.txt`, `backend/migrations/001_clientes.sql`, `frontend/config.js`, `frontend/clientes/clienteFacade.js`, `frontend/clientes/clienteRepository.js`, `index.html`, `.env.example`, `.gitignore` y los dos diagramas enlazados arriba.

## Esquema y migración

El script crea `empresas`, `talleres` (FK hacia empresa) y `clientes` (FK `taller_id` hacia talleres). Campos de clientes: `id`, `taller_id`, `nombre_completo`, `contacto_alterno`, `edad`, `fecha_nacimiento`, `telefono_personal`, `telefono_trabajo`, `email`, `email_trabajo`, `foto_ruta`, `calle`, `colonia`, `municipio`, `estado`, `codigo_postal`, `creado_por`, `created_at`, `updated_at`. `email_trabajo` y `foto_ruta` permiten `NULL`. Hay índices de taller/email/teléfono y unicidad por taller para email, teléfono y combinación nombre+fecha.

`creado_por` no tiene FK porque el repositorio no contiene tabla de usuarios. Antes de producción debe definirse esa relación y confirmar compatibilidad del tipo de `usuario_id`.

### Pasos locales

1. Instala Python 3.10+ y MySQL/MariaDB. Crea una base vacía y configura `.env` (no lo agregues a Git) a partir de `.env.example`; completa `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y genera `APP_SECRET_KEY`.
2. Inserta una fila en `empresas` y un taller asociado en `talleres`. El login debe incluir ese taller en su sesión.
3. Instala las dependencias: `python3 -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt`.
4. Aplica una sola vez el esquema: `set -a; . ./.env; set +a; mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p "$DB_NAME" < backend/migrations/001_clientes.sql` (el CLI solicitará la contraseña; evita ponerla en el comando/historial).
5. Inicia la API desde la raíz: `python backend/app.py`. `APP_PORT` define el puerto (5000 por defecto en el código).
6. Para dar de alta desde el panel, el login debe autenticar y establecer cookie de sesión firmada con `session['usuario'] = {usuario_id, rol, taller_id}`. Sin esa integración la API bloquea las rutas protegidas.

## Configuración y despliegue

El backend usa `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y `APP_SECRET_KEY`; `APP_PORT`, `APP_HOST`, `CORS_ORIGIN` y `SESSION_COOKIE_SECURE` ajustan servicio, origen permitido y cookie HTTPS. `.env` y `storage/clientes/` están ignorados por Git. En hosting configura las mismas variables en el panel de secretos, `APP_HOST=0.0.0.0`, MySQL gestionado privado, `CORS_ORIGIN` igual al dominio HTTPS frontend, `SESSION_COOKIE_SECURE=true`; nunca pongas contraseña de BD en Vue.

El frontend es estático y carga Vue/Tailwind/Bootstrap por CDN. Puede desplegarse en Netlify, Cloudflare Pages o un servidor estático publicando la raíz del repositorio; no tiene build command. `frontend/config.js` define `window.API_BASE_URL` para el backend; al desplegarlo reemplaza el localhost por el host HTTPS de la API y define CORS/cookie para el dominio del frontend. No está listo para un despliegue funcional hasta integrar el login de sesión.

## Verificación realizada

- Repositorio revisado: no había backend ni acceso al MySQL. No se ejecutó alta/duplicado real. Para verificarla hacen falta `.env`, tablas de empresa/taller y sesión de usuario/rol/taller que el login actual no proporciona.
- Instalación solicitada de Archify: **falló**, `/bin/bash: npx: command not found`; el diagrama adjunto se creó manualmente a partir del código incluido.
- Estado global del módulo: **en progreso**; la ruta funcional de extremo a extremo depende de conectar login, sesión y MySQL locales.
