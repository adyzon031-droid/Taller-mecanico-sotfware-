# Fase 02 · Registro de clientes

## Análisis previo

1. El login original de `index.html` era demostrativo y no autenticaba contra el backend.
2. No existían sesión, roles persistidos, guard de rutas ni vínculo del usuario con un taller.
3. El proyecto ya establece MySQL en `.env.example`; se conserva ese motor y se añadió configuración Flask/MySQL.
4. El login consulta `/api/auth/login`; el backend busca por email con SQL parametrizado, comprueba bcrypt y firma una cookie HttpOnly con usuario, rol y taller.
5. `.env` existe y está ignorado por Git; se comprobó la conexión local sin imprimir sus valores. La contraseña de un usuario real no fue proporcionada para validar un inicio exitoso.

## Arquitectura y módulos

Flujo del registro: **Vista Vue → ClienteFacade frontend → ClienteRepository frontend → API REST Flask → ClienteFacade backend → ClienteRepository backend → MySQL**. El Repository backend ejecuta SQL parametrizado. El formulario nunca accede directamente a la API. Al registrar una fotografía, el navegador envía datos y foto en un multipart; el backend inserta la fila, mueve la foto dentro de la transacción y confirma. Si hay error, hace rollback y elimina el archivo.

| Actividad | Estado (Realizada/Pendiente/Verificada) | Observaciones |
|---|---|---|
| Login contra servicio | Realizada | `AuthFacade` llama a `/api/auth/login`; password se valida con bcrypt y se firma sesión. Petición con cuenta ficticia respondió 401; prueba exitosa con usuario real pendiente. |
| Conexión local y carga de `.env` | Verificada | `backend/db.py` carga el `.env` de la raíz sin sobreescribir variables del proceso; timeout acotado, charset utf8mb4 y `autocommit=False`. `SELECT 1` pasó y la conexión cerró correctamente. |
| Alta administrativa de usuarios | Realizada | `backend/manage_users.py` solicita contraseña interactivamente y guarda solo hash bcrypt; requiere MySQL configurado y taller existente. |
| Guard de rol y taller en backend | Realizada | Rutas protegidas comprueban sesión, `usuario_id`, taller y exactamente los roles `administrador`/`recepcionista`, alineados con el ENUM de la BD; Vue usa la misma lista como control visual. |
| Visibilidad/guard de acceso del formulario | Realizada | Vue oculta el acceso a Clientes según el rol devuelto por sesión y comprueba el permiso antes de abrirlo. El backend es la autoridad final. |
| Formulario por secciones y validación inmediata | Realizada | Datos personales, contacto, fotografía y dirección; mensajes breves por campo, email/teléfonos/CP/edad y obligatorios. |
| Vista previa y validación de foto | Realizada | JPG/JPEG/PNG/WEBP, 15 MB máximo; frontend valida tipo/tamaño y backend extensión/firma/tamaño. |
| Facade y Repository frontend | Realizada | La Vista llama a `ClienteFacade`; su Repository transporta JSON/multipart y cookie de sesión. |
| API de clientes y duplicados | Realizada | POST 201, duplicados 409, inválidos 422, listado/consulta/PUT/foto/verificar duplicado. Restricciones UNIQUE cubren carreras concurrentes. |
| Transacción conjunta de cliente y foto | Realizada | `ClienteRepository.crear()` inserta, mueve archivo temporal y confirma; rollback elimina la foto final o temporal. Falta prueba integrada. |
| Esquema MySQL local | Verificada | Existen `empresas`, `talleres`, `usuarios`, `clientes`; las FK empresa→taller, taller→usuario y taller→cliente se confirmaron. Conteos: 1 empresa, 1 taller, 2 usuarios, 0 clientes. No se ejecutaron migraciones ni se alteraron datos. |
| Dependencias Python en `.venv` | Verificada | El entorno existente importa Flask, PyMySQL, python-dotenv y bcrypt; se levantó una instancia temporal de API en puerto 5001. |
| Alta real, duplicados, formato y foto con sesión | Pendiente | No se enviaron clientes ni se alteraron datos; requieren una credencial autorizada. El guard denegó el rol `gerente` con 403 en prueba aislada. |
| Instalación/uso de Archify | Pendiente | `node`/`npx` están disponibles, pero la clonación del repositorio falló por conexión HTTPS a GitHub. Se dejó diagrama manual HTML autónomo más SVG. |
| Commit | Verificada | Commit local `Completa registro de clientes fase 2` creado. |
| Push no forzado | Pendiente | `git push -u origin master` quedó sin respuesta durante 30 segundos y se interrumpió; el remoto no confirmó publicación. No se usó force. |

**Usuarios y contraseñas:** MySQL ya contiene 2 cuentas; no se muestran sus datos ni se conocen sus contraseñas. El login está enlazado a la tabla y validó el rechazo de credenciales ficticias. No reutilices la contraseña de MySQL como clave de aplicación. Para altas autorizadas, `python backend/manage_users.py` solicita contraseña con prompt oculto, aplica bcrypt (coste 12) y crea solo roles administrador/recepcionista.

## Documentación del código

### Frontend

| Función/método | Capa | Propósito | Parámetros → retorno |
|---|---|---|---|
| `AuthFacade.login(email,password)` | Facade de acceso | Comprueba campos y delega al repository. | Correo/contraseña → Promise de sesión. |
| `AuthFacade.logout()` / `sesion()` | Facade de acceso | Cierra o restaura la sesión. | Sin parámetros → Promise JSON. |
| `AuthRepository.request(path,body)` | Repository de acceso | Envía POST JSON con cookie `credentials: include`; convierte respuestas fallidas en Error. | Ruta/objeto → Promise JSON. |
| `ClienteFacade.errores(cliente)` | Facade clientes | Devuelve errores por campo: requeridos, email, teléfono, CP, edad/fecha y foto. | Cliente → mapa campo/mensaje. |
| `ClienteFacade.validar(cliente)` | Facade clientes | Lanza Error con `fieldErrors` cuando hay datos inválidos. | Cliente → `undefined` o Error. |
| `ClienteFacade.registrar(cliente)` | Facade clientes | Valida, busca duplicado, crea registro y emite notificación de éxito/error. | Cliente → Promise JSON; maneja errores 409/422 y sesión. |
| `ClienteFacade.listar(filtros)` | Facade clientes | Delega listado filtrado. | Filtros → Promise JSON. |
| `ClienteRepository.request(path,options)` | Repository clientes | Envía REST JSON o multipart y procesa códigos HTTP. | Ruta/opciones → Promise JSON. |
| `listar`, `consultar`, `crear`, `actualizar`, `verificarDuplicado`, `subirFoto` | Repository clientes | Envolturas para los endpoints REST. `crear(cliente,foto)` envía foto junto con los datos. | Filtro/id/datos/archivo → Promise JSON. |
| `login`, `logout`, `abrirClientes`, `tocarCampo`, `revalidarCampo`, `calcularEdad`, `seleccionarFoto`, `quitarFoto`, `limpiarCliente`, `registrarCliente` | Vista Vue (`index.html`) | Interfaz, campos, mensajes, preview, permiso visual y envío por facade. | Eventos/formulario → estado Vue y promesa interna. |

### Backend

| Método/ruta | Capa | Propósito y parámetros | Retorno |
|---|---|---|---|
| `POST /api/auth/login` | `app.py` | Recibe email/password, autentica y coloca identidad firmada en sesión. | `200 {usuario}` o `401`. |
| `POST /api/auth/sesion` | `app.py` | Devuelve usuario de sesión existente. | `200` o `401`. |
| `POST /api/auth/logout` | `app.py` | Vacía sesión. | `200`. |
| `AuthFacade.autenticar(correo,password)` | Facade auth | Busca cuenta activa y verifica hash bcrypt; nunca devuelve hash. | Usuario (`usuario_id,nombre,rol,taller_id`) o `None`. |
| `AuthRepository.buscar_por_correo(correo)` | Repository auth | SELECT parametrizado de cuenta por correo. | Fila o `None`. |
| `AuthRepository.crear_usuario(nombre,correo,password_hash,rol,taller_id)` | Repository auth | Inserta cuenta dentro de transacción. | ID de cuenta. |
| `main()` | Herramienta local | Solicita datos/contraseña con `getpass`, genera bcrypt y crea una cuenta. | Imprime ID/correo/rol/taller; no imprime contraseña. |
| `requiere_rol(view)` | Guard Flask | Exige sesión, `usuario_id`, `taller_id` y rol autorizado. | Ejecuta vista o HTTP 401/403. |
| `validar(datos)` | Facade clientes | Valida formato y coherencia edad/fecha, completa opcionales. | Diccionario limpio o `ClienteError(422)`. |
| `ClienteFacade.crear(datos,sesion,foto_contexto,foto_ruta)` | Facade clientes | Añade taller/usuario desde sesión, busca duplicados y delega transacción. | ID o `ClienteError(409/422)`. |
| `ClienteFacade.listar/obtener/actualizar(sesion,...)` | Facade clientes | Delega operaciones dentro del taller activo. | Lista/fila/booleano. |
| `ClienteRepository.crear(valores,foto_contexto)` | Repository clientes | INSERT parametrizado, mueve foto temporal y commit; rollback limpia BD/archivo. | ID generado. |
| `ClienteRepository.listar/obtener/actualizar/duplicado/guardar_foto_y_actualizar` | Repository clientes | Ejecuta consultas parametrizadas; las modificaciones usan transacción. | Filas/booleano. |
| `connect()` | Infraestructura datos (`backend/db.py`) | Carga `.env` desde la raíz si el proceso no define las variables; valida DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD y DB_CONNECT_TIMEOUT. Abre PyMySQL con timeouts y autocommit desactivado. | Conexión; los Repository la cierran en `finally`. |
| `POST /api/clientes` | `crear_cliente` | Acepta JSON o multipart con `cliente` JSON y `foto` opcional. Taller/usuario salen de sesión. | `201`, `409`, `422`, `401/403`. |
| `GET /api/clientes` | `listar_clientes` | Filtros opcionales por nombre/email/teléfono; taller se toma de sesión. | `200 {clientes}`. |
| `GET /api/clientes/{id}` | `consultar_cliente` | ID dentro del taller activo. | `200` o `404`. |
| `PUT /api/clientes/{id}` | `actualizar_cliente` | Valida cuerpo completo y actualiza dentro del taller. | `200/404/409/422`. |
| `POST /api/clientes/{id}/foto` | `subir_foto` | Carga independiente para cliente existente; comprueba extensión/firma/tamaño y ruta. | `201/404/422`. |
| `GET /api/clientes/verificar-duplicado` | `verificar_duplicado` | Revisa email, teléfono y nombre+fecha en taller activo. | `200 {duplicado}`. |

## Datos y migraciones

`001_clientes.sql` crea `empresas`, `talleres` (FK a empresas) y `clientes`. `clientes`: `id`, `taller_id`, `nombre_completo`, `contacto_alterno`, `edad`, `fecha_nacimiento`, `telefono_personal`, `telefono_trabajo`, `email`, `email_trabajo NULL`, `foto_ruta NULL`, `calle`, `colonia`, `municipio`, `estado`, `codigo_postal`, `creado_por`, `created_at`, `updated_at`. Incluye índices en taller/email/teléfono; UNIQUE por taller en email, teléfono y nombre+fecha; FK de taller a talleres.

`002_usuarios_auth.sql` crea `usuarios` con `id`/`taller_id` BIGINT UNSIGNED, `nombre` VARCHAR(160), `email` VARCHAR(190) UNIQUE, `password_hash` VARCHAR(255), rol ENUM(`administrador`,`recepcionista`), activo y `created_at`; la FK usa el mismo tipo de `talleres.id`. Bcrypt produce el hash al crear cada cuenta. La tabla local ya existía y coincide con los campos que consulta AuthRepository; no se ejecutó la migración. `creado_por` no tiene FK a usuarios en 001 por el orden de migración/tipo previo; queda por añadir una FK revisada tras migrar 002.

### Conexión y arranque local

La BD local ya responde `SELECT 1`. `.env` está presente, no está versionado y sus permisos locales se restringieron a 600. `.env.example` enumera las variables sin valores secretos. No se corrieron migraciones: el esquema ya existe y se respetó.

1. Usa Python 3.10+, MySQL y el entorno existente `.venv`. Si falta, crea `.venv` e instala `pip install -r backend/requirements.txt`.
2. Completa `.env` local con `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_CONNECT_TIMEOUT`, `APP_SECRET_KEY`, `APP_HOST`, `APP_PORT`, `CORS_ORIGIN` y `SESSION_COOKIE_SECURE`. Genera el secreto con `python -c "import secrets; print(secrets.token_urlsafe(48))"`; guarda el resultado solo en `.env`. No copies claves reales a `.env.example`.
3. En producción, crea una cuenta MySQL dedicada con permisos mínimos sobre la base del taller; no uses root. En local usa el usuario MySQL ya configurado.
4. En esta BD ya existen 1 empresa y 1 taller. Hay 2 usuarios, pero sus contraseñas no se consultan ni se recuperan. Para crear una cuenta nueva, ejecuta `.venv/bin/python backend/manage_users.py` y asigna contraseña nueva en el prompt oculto.
5. Para una BD vacía, aplica solo las migraciones pendientes en el orden documentado: `001_clientes.sql`, luego `002_usuarios_auth.sql`; revisa primero que tablas/columnas no existan. En la BD actual no ejecutar estas migraciones porque las tablas están creadas.
6. Inicia API con `.venv/bin/python backend/app.py`. El frontend debe servirse por HTTP en el origen indicado por `CORS_ORIGIN`; `file://` tiene origen `null` y no sirve para una sesión con CORS/cookies. La API y el repositorio verifican cookie `HttpOnly`, `SameSite=Lax`; en HTTPS fija `SESSION_COOKIE_SECURE=true`.
7. Para previsualizar, se usó un directorio temporal con enlaces solo a `index.html` y `frontend/`, servidor en `127.0.0.1:4173`; `/.env`, `/backend/` y `/.git/` devolvieron 404. El proceso temporal se detuvo al terminar y el puerto quedó libre. No sirvas la raíz del repositorio.

## Diagrama de componentes

[HTML autónomo](docs/diagramas/fase-02-componentes-registro-clientes.html) (SVG inline, sin dependencias externas) · [Exportación SVG](docs/diagramas/fase-02-componentes-registro-clientes.svg). El HTML permite descargar el SVG.

Archify se intentó con el comando solicitado. No se pudo clonar su repositorio: `Failed to connect to github.com port 443`. Node v20.19.2 y npx v9.2.0 sí están disponibles; el diagrama alternativo se creó a mano usando los archivos implementados.

## Resultado real de pruebas

| Prueba | Estado | Resultado observado |
|---|---|---|
| `SELECT 1` desde `.venv` | Verificada | Devolvió 1; conexión cerrada correctamente. |
| `SHOW TABLES`, `DESCRIBE`, relaciones y conteos | Verificada | Cuatro tablas: `empresas`, `talleres`, `usuarios`, `clientes`; FK empresa→taller, taller→usuario y taller→cliente; conteos 1/1/2/0. No se leyeron filas personales ni se ejecutaron migraciones. |
| Variables y seguridad local | Verificada | `.env` existe, Git lo ignora, no está versionado; permisos locales ajustados a 600. Variables presentes y secreto de sesión de longitud ≥32; valores nunca impresos. |
| Instancia Flask temporal `127.0.0.1:5001` | Verificada | Arrancó con `.env` y se cerró tras la prueba. |
| `POST /api/auth/login` con usuario ficticio | Verificada | HTTP 401 con respuesta genérica; no se modificaron cuentas. |
| `GET /api/clientes` sin sesión | Verificada | HTTP 401. |
| Guard con rol `gerente` | Verificada | Flask test client devolvió 403; allowlist del backend es `administrador,recepcionista`. No se escribió en BD. |
| Preflight CORS desde `http://127.0.0.1:4173` a API 5000 | Verificada | CORS devolvió solo ese origen y `Allow-Credentials: true`; no usa `*`. |
| Frontend temporal y CORS | Verificada | El formulario cargó desde `127.0.0.1:4173`; credenciales ficticias fueron rechazadas. CORS permite solo ese origen y cookies. `/.env`, `/backend/` y `/.git/` dieron 404. Servidor detenido y puerto 4173 libre. |
| Sintaxis Python (`.venv/bin/python -m py_compile backend/*.py`) | Verificada | Compilación sin errores. |
| Login exitoso de usuario real | Pendiente | No se proporcionó contraseña válida; no se adivinó, cambió ni restableció ninguna. |
| Alta cliente, duplicado, formato, foto y rol | Pendiente | No se insertaron filas de prueba. Requiere sesión de usuario autorizada; `clientes` sigue con 0 filas. |
| Instalación de Archify | Pendiente | Falló al conectar con `github.com:443`; diagrama manual conservado. |

## Seguridad de contraseñas

Las contraseñas de cuentas se reciben mediante prompt oculto y se almacenan como hash bcrypt; el login compara el hash y no devuelve este dato. La BD tiene dos cuentas existentes, pero no se consultaron sus datos de identificación ni se conocen sus contraseñas. `python backend/manage_users.py` permite a una persona autorizada crear un usuario administrador o recepcionista y elegir su contraseña interactivamente. El secreto de sesión local existe y su longitud supera 32 caracteres; su valor no se revela. Recomendado antes de producción: HTTPS y cookies `Secure`, límite de intentos de login, protección CSRF apropiada para cookies, recuperación con token aleatorio de un solo uso y expiración, y cambio de contraseñas provisionales. Nunca reutilizar credenciales de MySQL como credenciales de usuario.

El HTML del diagrama es autocontenido y el SVG es independiente. Conexión a MySQL, esquema y manejo de sesión sin credenciales están verificados; el login exitoso y los flujos que escriben clientes quedan pendientes de una cuenta autorizada para prueba. No se agregan credenciales predeterminadas al código.
