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
| Esquema MySQL local | Verificada | Existen `empresas`, `talleres`, `usuarios`, `clientes`; las FK empresa→taller, taller→usuario y taller→cliente se confirmaron. Conteos de la inspección previa: 1 empresa, 1 taller, 2 usuarios y 0 clientes. El 1 de octubre de 2026, GET /api/clientes con sesión de prueba devolvió 1 registro activo; no se leyeron datos personales. La migración 003 añadió solo las dos columnas de baja lógica. |
| Dependencias Python en `.venv` | Verificada | El entorno existente importa Flask, PyMySQL, python-dotenv y bcrypt; se levantó una instancia temporal de API en puerto 5001. |
| Alta real, duplicados, formato y foto con sesión | Pendiente | No se enviaron clientes ni se alteraron datos; requieren una credencial autorizada. El guard denegó el rol `gerente` con 403 en prueba aislada. |
| Instalación/uso de Archify | Pendiente | `node`/`npx` están disponibles, pero la clonación del repositorio falló por conexión HTTPS a GitHub. Se dejó diagrama manual HTML autónomo más SVG. |
| Commit | Verificada | Commit local `Completa registro de clientes fase 2` y commit de conexión local creados. |
| Push no forzado | Pendiente | Tras autorización del remoto, `git push -u origin master` quedó esperando sin respuesta durante 40 segundos y se interrumpió; GitHub no confirmó publicación. No se usó force. |

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

`002_usuarios_auth.sql` crea `usuarios` con `id`/`taller_id` BIGINT UNSIGNED, `nombre` VARCHAR(160), `email` VARCHAR(190) UNIQUE, `password_hash` VARCHAR(255), rol ENUM(`administrador`,`recepcionista`), activo y `created_at`; la FK usa el mismo tipo de `talleres.id`. Bcrypt produce el hash al crear cada cuenta. La tabla local ya existía y coincide con los campos que consulta AuthRepository; no se ejecutó la migración 002 en la BD local. `creado_por` no tiene FK a usuarios en 001 por el orden de migración/tipo previo; queda por añadir una FK revisada tras migrar 002.

### Conexión y arranque local

La BD local ya responde `SELECT 1`. `.env` está presente, no está versionado y sus permisos locales se restringieron a 600. `.env.example` enumera las variables sin valores secretos. La migración aditiva `003_clientes_baja_logica.sql` se aplicó y repitió de forma idempotente; no se recrearon tablas ni se alteraron filas existentes.

1. Usa Python 3.10+, MySQL y el entorno existente `.venv`. Si falta, crea `.venv` e instala `pip install -r backend/requirements.txt`.
2. Completa `.env` local con `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_CONNECT_TIMEOUT`, `APP_SECRET_KEY`, `APP_HOST`, `APP_PORT`, `CORS_ORIGIN` y `SESSION_COOKIE_SECURE`. Genera el secreto con `python -c "import secrets; print(secrets.token_urlsafe(48))"`; guarda el resultado solo en `.env`. No copies claves reales a `.env.example`.
3. En producción, crea una cuenta MySQL dedicada con permisos mínimos sobre la base del taller; no uses root. En local usa el usuario MySQL ya configurado.
4. En esta BD ya existen 1 empresa y 1 taller. Hay cuentas existentes, pero sus identificadores y contraseñas no se consultan ni se recuperan. Para crear una cuenta nueva, ejecuta `.venv/bin/python backend/manage_users.py` y asigna contraseña nueva en el prompt oculto.
5. Para una BD vacía, aplica solo las migraciones pendientes en el orden documentado: `001_clientes.sql`, `002_usuarios_auth.sql` y `003_clientes_baja_logica.sql`; revisa qué objetos faltan antes de aplicar. La 003 usa `ADD COLUMN IF NOT EXISTS` y ya está aplicada en la BD local.
6. Inicia API con `.venv/bin/python backend/app.py`. El frontend debe servirse por HTTP en el origen indicado por `CORS_ORIGIN`; `file://` tiene origen `null` y no sirve para una sesión con CORS/cookies. La API y el repositorio verifican cookie `HttpOnly`, `SameSite=Lax`; en HTTPS fija `SESSION_COOKIE_SECURE=true`.
7. Para previsualizar, se usó un directorio temporal con enlaces solo a `index.html` y `frontend/`, servidor en `127.0.0.1:4173`; `/.env`, `/backend/` y `/.git/` devolvieron 404. El proceso temporal se detuvo al terminar y el puerto quedó libre. No sirvas la raíz del repositorio.

## Diagrama de componentes

[HTML autónomo](docs/diagramas/fase-02-componentes-registro-clientes.html) (SVG inline, sin dependencias externas) · [Exportación SVG](docs/diagramas/fase-02-componentes-registro-clientes.svg). El HTML permite descargar el SVG.

Archify se intentó con el comando solicitado. No se pudo clonar su repositorio: `Failed to connect to github.com port 443`. Node v20.19.2 y npx v9.2.0 sí están disponibles; el diagrama alternativo se creó a mano usando los archivos implementados.

## Resultado real de pruebas

| Prueba | Estado | Resultado observado |
|---|---|---|
| `SELECT 1` desde `.venv` | Verificada | Devolvió 1; conexión cerrada correctamente. |
| `SHOW TABLES`, `DESCRIBE`, relaciones y conteos | Verificada | Cuatro tablas: `empresas`, `talleres`, `usuarios`, `clientes`; FK empresa→taller, taller→usuario y taller→cliente; conteos vistos en la inspección inicial 1/1/2/0; el 1 de octubre de 2026, el listado real con sesión de prueba devolvió 1 cliente. No se inspeccionaron sus datos. No se leyeron filas personales ni se ejecutaron migraciones. |
| Variables y seguridad local | Verificada | `.env` existe, Git lo ignora, no está versionado; permisos locales ajustados a 600. Variables presentes y secreto de sesión de longitud ≥32; valores nunca impresos. |
| Instancia Flask temporal `127.0.0.1:5001` | Verificada | Arrancó con `.env` y se cerró tras la prueba. |
| `POST /api/auth/login` con usuario ficticio | Verificada | HTTP 401 con respuesta genérica; no se modificaron cuentas. |
| `GET /api/clientes` sin sesión | Verificada | HTTP 401. |
| Guard con rol `gerente` | Verificada | Flask test client devolvió 403; allowlist del backend es `administrador,recepcionista`. No se escribió en BD. |
| Preflight CORS desde `http://127.0.0.1:4173` a API 5000 | Verificada | CORS devolvió solo ese origen y `Allow-Credentials: true`; no usa `*`. |
| Frontend temporal y CORS | Verificada | El formulario cargó desde `127.0.0.1:4173`; credenciales ficticias fueron rechazadas. CORS permite solo ese origen y cookies. `/.env`, `/backend/` y `/.git/` dieron 404. Servidor detenido y puerto 4173 libre. |
| Sintaxis Python (`.venv/bin/python -m py_compile backend/*.py`) | Verificada | Compilación sin errores. |
| Login exitoso de usuario real | Pendiente | No se proporcionó contraseña válida; no se adivinó, cambió ni restableció ninguna. |
| Alta cliente, duplicado, formato, foto y rol | Pendiente | No se insertaron filas de prueba. Requiere sesión de usuario autorizada; la prueba de solo lectura del 1 de octubre de 2026 encontró 1 fila activa; sus datos personales no se leyeron ni imprimieron. |
| Instalación de Archify | Pendiente | Falló al conectar con `github.com:443`; diagrama manual conservado. |

## Seguridad de contraseñas

Las contraseñas de cuentas se reciben mediante prompt oculto y se almacenan como hash bcrypt; el login compara el hash y no devuelve este dato. La BD tiene dos cuentas existentes, pero no se consultaron sus datos de identificación ni se conocen sus contraseñas. `python backend/manage_users.py` permite a una persona autorizada crear un usuario administrador o recepcionista y elegir su contraseña interactivamente. El secreto de sesión local existe y su longitud supera 32 caracteres; su valor no se revela. Recomendado antes de producción: HTTPS y cookies `Secure`, límite de intentos de login, protección CSRF apropiada para cookies, recuperación con token aleatorio de un solo uso y expiración, y cambio de contraseñas provisionales. Nunca reutilizar credenciales de MySQL como credenciales de usuario.

El HTML del diagrama es autocontenido y el SVG es independiente. Conexión a MySQL, esquema y manejo de sesión sin credenciales están verificados; el login exitoso y los flujos que escriben clientes quedan pendientes de una cuenta autorizada para prueba. No se agregan credenciales predeterminadas al código.


## Estado de la ampliación CRUD de clientes y navegación

**Implementación actual:** navegación por hash con una única sección activa (incluye atrás/adelante y `aria-current="page"`); las pantallas sin implementar muestran “Próximamente”. Clientes incluye consulta, búsqueda, páginas de hasta 10 filas, detalle en solo lectura, edición reutilizando el formulario, foto opcional conservada y eliminación lógica solo para administrador. Recepcionista puede consultar, crear y editar. Todas las operaciones usan `taller_id` de la sesión; un ID de otro taller se trata como no encontrado.

### Campos y validación

| Campo | Regla | Dónde se valida |
|---|---|---|
| Textos y nombres | Trim y colapsar espacios; nombre de dos o más palabras; letras Unicode/acento/ñ, espacios, apóstrofo y guion. | `frontend/clientes/clienteFacade.js`, `backend/cliente_facade.py` |
| Contacto alternativo | Opcional; misma regla de nombre. | Facade frontend y backend |
| Teléfonos | Exactamente 10 dígitos guardados; prefijo +52 solo visual. Admite pegar espacios/guiones, descarta símbolos/letras en la vista y el backend rechaza formatos inválidos. | Vista `index.html`, facades frontend/backend |
| Correos | Formato válido, minúsculas, máximo 190; correo laboral opcional y distinto al personal. | Facades frontend/backend; UNIQUE y duplicado en repository |
| Nacimiento/edad | Fecha ISO real, no futura ni mayor a 120 años; edad readonly frontend y recalculada/verificada por backend. | Facades frontend/backend |
| Foto | JPG/JPEG/PNG/WEBP, máximo 15 MiB; extensión, MIME y firma binaria validados por backend; UUID en almacenamiento. | Vista y `backend/app.py` |
| Dirección | CP de cinco dígitos y estado de catálogo fijo con 32 entidades; municipio y colonia manuales porque no hay catálogo local. | Facades frontend/backend y vista |
| Duplicidad | Correo, teléfono y nombre+fecha dentro del taller; edición excluye su propio ID; conflictos UNIQUE se convierten a 409. | Facades/repositories y handler Flask |

### API REST ajustada

| Método y ruta | Respuesta y alcance |
|---|---|
| `GET /api/clientes?q=&page=&per_page=` | Lista/búsqueda dentro del taller de la sesión; `per_page` limitado a 10. |
| `GET /api/clientes/{id}` | Detalle o 404 si no pertenece al taller/está eliminado. |
| `PUT /api/clientes/{id}` | Actualiza datos; multipart para foto opcional o JSON sin cambiar la existente. Respuestas 200/404/409/422. |
| `DELETE /api/clientes/{id}` | Solo administrador; marca `activo=0` y `deleted_at`, conserva fila/foto; 200/403/404. |
| `GET /api/clientes/{id}/foto` | Devuelve foto solo para cliente activo del taller actual. |
| `GET /api/clientes/verificar-duplicado` | Revisión previa por campo; el guard obtiene taller desde sesión. |
| `POST /api/clientes` | Conserva el alta previa; 201/409/422 y foto opcional. |

`backend/cliente_facade.py` normaliza/valida, aplica duplicados y llama al repository. `backend/cliente_repository.py` limita cada lectura/escritura con `taller_id`, une paginación y baja lógica y cierra conexiones en `finally`. `backend/app.py` establece las rutas, sesión/roles, manejo de error, validación de firma fotográfica y servicio protegido de foto. `frontend/clientes/clienteFacade.js` coordina validación, CRUD, errores/notificaciones; `clienteRepository.js` es el único transporte REST desde Vue.

### Migración y pruebas

Se agregó `backend/migrations/003_clientes_baja_logica.sql`, solo aditiva e idempotente (`activo DEFAULT 1`, `deleted_at NULL`). Se aplicó en MariaDB 11.8.6 local y se ejecutó una segunda vez: ambas columnas presentes tras ambas ejecuciones. No se borraron filas ni fotos.

Suite `backend/tests/test_clientes.py`, ejecutada con `.venv/bin/python -m pytest -q backend/tests`: **28 passed**. Son pruebas unitarias y de Flask con dependencias simuladas para validar formato, 409, foto grande, permisos y 404 de otro taller; no sustituyen una prueba extremo a extremo CRUD con login y escritura en MySQL real. Edición sin cambiar foto se verificó con repository simulado; no se insertaron datos reales de clientes.

**Pendiente:** catálogo SEPOMEX local/autocompletado por CP; pruebas E2E con cuenta de sesión autorizada; separar y configurar entorno de pruebas MySQL si se requiere validar consultas reales de escritura. El catálogo oficial se descarga desde [Correos de México / SEPOMEX](https://www.correosdemexico.gob.mx/sslservicios/consultacp/CodigoPostal_Exportar.aspx).

## CU-B02: Gestión de clientes

`planeacion_faseinicial.md` no contiene un caso CU-B02 identificable; se usa el título de respaldo indicado para esta documentación. La fase extendida mantiene las capacidades anteriores y agrega identidad mexicana, gestión por empresa/taller, filtros y suspensión reversible.

| ID | Nombre | Actores | Precondiciones | Postcondiciones | Flujo principal | Flujos alternos | Reglas de negocio | Privilegios por rol |
|---|---|---|---|---|---|---|---|---|
| CU-B02 | Gestión de clientes | Administrador, recepcionista | Sesión autenticada; taller activo asociado. Catálogos de ubicación y país disponibles para validación. | Cliente creado/consultado/actualizado dentro del alcance autorizado, o estado actualizado por administrador. | 1. Abrir Clientes. 2. Buscar, filtrar, ordenar o paginar en servidor. 3. Mostrar ficha o abrir formulario. 4. Backend valida identidad, contacto, dirección y duplicados. 5. Repository aplica la operación con ámbito de empresa/taller. 6. Vista muestra resultado. | Datos inválidos: 422 por campo; duplicado: 409; sesión requerida: 401; rol no permitido: 403; objeto ajeno/no disponible: 404; catálogo no disponible: mensaje de error. El administrador elige taller al crear y puede consultar los talleres de su empresa. | Nombre completo derivado; normalización en backend; CURP y RFC validados localmente (sin consulta al SAT); contactos y direcciones validados; unicidad por taller; clasificación SQL de ordenamiento en lista blanca; página 10/25/50; motivo de suspensión opcional; baja lógica existente se conserva. | Administrador: ámbito empresa, asigna taller, puede suspender/reactivar y usar baja lógica. Recepcionista: solo su taller, puede consultar/crear/editar; no suspende, reactiva ni elimina. Cliente de otro ámbito no se revela (404). |

## Trazabilidad de implementación de esta fase

Estados: **Verificada** significa que la prueba indicada pasó; **Realizada** significa código/migración presente, pero no hay prueba funcional suficiente para declararla verificada; **Pendiente** significa que falta completar o comprobar el alcance descrito.

| Actividad | Capa | Archivo | Método/función | Estado (Realizada/Pendiente/Verificada) | Evidencia/prueba |
|---|---|---|---|---|---|
| Extender talleres con contacto, dirección, RFC, foto y estado, sin quitar columnas existentes | Datos | `backend/migrations/006_gestion_talleres.sql` | migración SQL aditiva | Verificada | Aplicada a la BD local; la fila de taller existente se conservó; índices únicos de empresa/taller instalados. |
| Ampliar identidad y estado de clientes, conservar datos legados y admitir contactos opcionales | Datos | `backend/migrations/007_clientes_identidad_y_estado.sql` | migración SQL aditiva | Verificada | Aplicada y repetida idempotentemente; celular/nombres legados copiados solo donde faltaban; teléfono laboral permite NULL. |
| Normalizar textos e identidad fiscal mexicana | Dominio | `backend/identidad_mexico.py` | `normalizar_palabras`, `validar_curp`, `validar_rfc_persona_fisica` | Verificada | Suite pytest cubre normalización, CURP/RFC, fechas, coherencia y verificador. No consulta SAT. |
| Validar, normalizar y coordinar altas, ediciones, estados y duplicados de cliente | Dominio/API | `backend/cliente_facade.py` | `validar`, `_target_workshop`, `crear`, `listar`, `obtener`, `actualizar`, `suspender`, `reactivar`, `eliminar` | Verificada | Pruebas de formato, duplicados, permisos y estado; suite completa: 58 pasadas. |
| Consultas SQL de clientes aisladas por sesión/taller, filtros y paginación | Persistencia | `backend/cliente_repository.py` | `_run`, `_scope`, `crear`, `listar`, `obtener`, `actualizar`, `duplicado`, `estado`, `eliminar`, `talleres_empresa`, operaciones de foto | Verificada | Pruebas de acceso por taller, alcance de recepcionista, orden y paginación; conexión real MySQL disponible en la ejecución de suite. No se imprimieron filas personales. |
| Validar y coordinar CRUD/estado de taller | Dominio | `backend/taller_facade.py` | `_validate`, `listar`, `obtener`, `crear`, `actualizar`, `set_estado` | Realizada | La validación de taller está implementada; no se hizo recorrido autenticado de navegador contra los endpoints. |
| Consultas y persistencia de talleres con ámbito de empresa | Persistencia | `backend/taller_repository.py` | `_one`, `_many`, `empresa_de_taller`, `listar`, `obtener`, `crear`, `actualizar`, `actualizar_foto`, `estado` | Realizada | CRUD implementado con consultas parametrizadas; no se probó el ciclo completo de escritura en navegador. |
| Catálogo de países y búsqueda/validación SEPOMEX | Dominio y persistencia | `backend/ubicacion_facade.py`, `backend/ubicacion_repository.py`, `backend/data/`, `data/` | `paises`, `cp`, `estados`, `municipios`, `colonias`, `buscar`, `direccion_valida`, consultas de catálogo | Verificada | Suite cubre ubicación/teléfonos; los endpoints de catálogo quedan disponibles para las facades. |
| Rutas API, sesión/roles, respuestas y validación de fotos | API | `backend/app.py` | `login`, `consultar_sesion`, `cerrar_sesion`, rutas `/api/talleres`, `/api/clientes`, `/api/ubicacion`, `_validar_foto`, manejadores 409/422 | Realizada | Compilación Python sin error y pruebas de Flask en suite; respuesta 401 de API sin sesión consta en registros de fase previos. Flujo CRUD real autenticado pendiente. |
| Autenticación y contexto de empresa/taller en sesión | API/persistencia | `backend/auth_facade.py`, `backend/auth_repository.py` | validación de login; consulta de usuario y taller activo | Realizada | La consulta de autenticación incorpora empresa y taller, filtrando taller activo. No se probó ingreso exitoso en el navegador. |
| Facade y transporte REST para clientes y ubicación | Frontend | `frontend/clientes/clienteFacade.js`, `frontend/clientes/clienteRepository.js` | validación/normalización, CRUD, duplicidad, filtros; transporte REST y catálogo | Verificada | `node --check` sin errores. La validación visual de pantallas tras autenticación queda pendiente. |
| Facade y transporte REST de talleres | Frontend | `frontend/talleres/tallerFacade.js`, `frontend/talleres/tallerRepository.js` | validación/normalización, CRUD/estado; transporte REST y foto | Verificada | `node --check` sin errores. Las operaciones protegidas requieren sesión válida y no se probaron en navegador. |
| Formularios, fichas, navegación, validación local, filtros, sort/paging y permisos visibles | Vista | `index.html` | componentes Vue, formularios y manejadores de eventos | Realizada | La página de login cargó en el navegador. No se pudo probar ficha/CRUD, taller ni visibilidad por rol sin iniciar sesión autorizada. |
| Exclusión de almacenamiento de fotos de taller | Configuración | `.gitignore` | regla `storage/talleres/` | Verificada | Regla presente junto a exclusiones preexistentes para secretos y fotos de cliente; no se ejecutaron comandos Git. |
| Verificación automatizada | Pruebas | `backend/tests/test_clientes.py`, `backend/tests/test_fase02_extendida.py`, `backend/tests/test_phone_location.py` | pruebas pytest de dominio, API, permisos, duplicados, identidad, foto, ubicación, orden y paginación | Verificada | `.venv/bin/pytest -q`: 58 passed. `python -m py_compile backend/*.py` y `node --check` para módulos frontend: sin errores. |
| Aislamiento de servidor temporal del proyecto | Navegador/servidor local | Solo archivos existentes `index.html` y `frontend/` | HTTP local en `127.0.0.1` | Verificada | `/index.html` y `/frontend/`: 200; `/.env`, `/backend/` y `/.git/`: 404. Servidor detenido y puerto comprobado libre. No se usó `.env` para servir archivos. |

### Revisión de esquema y estado comprobado

La inspección estructural de esta ampliación encontró 1 empresa, 1 taller, 4 usuarios y 4 clientes. Se consultaron cantidades y columnas, no valores identificables de clientes ni credenciales. Las migraciones `006` y `007` preservaron las filas existentes; las columnas nuevas están presentes y el campo `telefono_trabajo` acepta NULL. No se borraron ni recrearon tablas.

**Pendiente:** probar con sesión válida en navegador el alta/edición/suspensión de taller y cliente, ficha de cliente, los filtros y la presentación de botones según rol. La ejecución actual solo mostró el login y verificó que el servidor temporal no publicara backend, `.env` ni `.git`.

## Actualización de módulos de estatus y vehículos · 8 de octubre de 2026

Esta sección actualiza el estado de la implementación ampliada; las notas históricas anteriores se conservan. La migración `012_estatus_clientes_vehiculos.sql` se aplicó y se repitió sin error en la BD local. Conteos agregados posteriores: 7 estatus activos, 22 marcas activas, 111 modelos activos, 4 clientes activos y 1 vehículo eliminado lógicamente (fila conservada). No se consultaron ni documentaron valores personales.

| Módulo | Datos / entidades | Estado | Solución implementada y evidencia |
|---|---|---|---|
| Catálogo de estatus | `estatus(id, valor, descripcion, es_sistema, activo, created_at, updated_at)`; clientes, marcas y modelos conservan sus FK | Verificada | Migración aditiva/idempotente conserva IDs legados 1–3, agrega los 4 valores restantes y columnas del catálogo; siete opciones comprobadas en la BD. API CRUD sin DELETE; el uso bloquea desactivar; permisos por rol cubiertos por pytest. Pantalla de administración cargó con sesión válida. |
| Estado y baja lógica de clientes | `clientes.estatus_id`, motivo/fecha/usuario de suspensión y baja lógica | Verificada | Estatus ID es la fuente consultada; suspensión/reactivación con bloqueo transaccional y comprobación del estado; acciones según rol. Se probó suspensión y reactivación desde navegador, con regreso a 4 clientes activos. |
| Edición de cliente | Campos existentes de `clientes` y `cliente_contactos` | Verificada parcialmente | Formulario abre como diálogo accesible y se cierra con Escape; no se guardó una edición en esta pasada. Conflicto de concurrencia y actualización real quedan pendientes. |
| Paginación común | Parámetros `page`, `page_size`, `sort`, `direction`; resultado `items/page/page_size/total/total_pages` | Verificada parcialmente | `backend/pagination.py` normaliza tamaños a 10/25/50 y valida listas permitidas; pytest comprueba orden, filtros y límite 50 en clientes. Estatus y vehículos tienen listado paginado. Talleres aún no están integrados al helper común. |
| Gestión de vehículos | `vehiculos`, FK a taller/cliente/estatus/marca/modelo; placa y serie vigentes únicas; baja lógica | Verificada parcialmente | Migración crea la tabla. API crea/consulta/edita y elimina/restaura sin borrar filas; catálogo pendiente se enlaza en la transacción. En navegador se comprobó autocompletado de marca/modelo, placa normalizada y disponible, alta HTTP 201, “Registrar otro”, listado y baja lógica. No se verificaron en navegador edición, filtro completo, restauración ni advertencias bajo cada campo. |
| Integración del catálogo de marcas/modelos | `marcas`, `modelos`, `estatus_id` | Verificada parcialmente | Adaptado el uso de `estatus.valor` y la forma de las opciones para el autocomplete. Conteos activos confirmados. Bloqueo de desactivación por vehículos asociados y enlace retroactivo de vehículos existentes requieren verificación funcional adicional. |
| API y facades de estatus/vehículos | `/api/estatus*`, `/api/vehiculos*`, `/api/clientes/{id}/vehiculos` | Verificada parcialmente | Rutas protegidas con sesión/roles; repositories aíslan acceso SQL. Pruebas automatizadas completas y alta/baja de vehículo en navegador. No se recorrieron todas las rutas CRUD con usuario real. |

### Código nuevo o adaptado

| Archivo/capa | Funciones principales | Propósito |
|---|---|---|
| `backend/estatus_facade.py` | `validate(data)` | Normaliza y valida valor y descripción antes de persistir. |
| `backend/estatus_repository.py` | `list`, `options`, `get`, `save`, `activate` | Consultas y cambios parametrizados; limita cambios de sistema y desactivación cuando hay referencias. |
| `backend/vehiculo_facade.py` | `validate(data)`, `create(user,data)` | Valida, normaliza y coordina el registro; devuelve errores de campo y advertencias. |
| `backend/vehiculo_repository.py` | `_status`, `_scope`, `list`, `get`, `verify_plate`, `create`, `update`, `change_deleted`, `by_client` | Aísla por taller, consulta paginada, comprueba unicidad y realiza altas/cambios/bajas lógicas transaccionales. |
| `backend/pagination.py` | `parse_page`, `page_result` | Normaliza página/tamaño y limita orden a columnas permitidas; arma metadatos de paginación. |
| `frontend/estatus/estatusFacade.js`, `estatusRepository.js` | métodos de consulta, opciones, alta, edición y estado | La vista delega en Facade; Repository envía las peticiones HTTP autenticadas. |
| `frontend/vehiculos/vehiculoFacade.js`, `vehiculoRepository.js` | métodos de lista, ficha, placa, alta, edición y baja/restauración | Orquestan validación y API desde la pantalla de vehículos. |
| `frontend/vehiculoAutocomplete.js` | búsqueda/selección de marca y modelo | Convierte las opciones API en sugerencias y permite proponer valores que el backend crea como pendientes. |
| `backend/migrations/012_estatus_clientes_vehiculos.sql` | migración repetible | Actualiza estatus, agrega estado a clientes y crea tabla/índices de vehículos sin eliminar filas existentes. |

### Rutas añadidas

- `GET /api/estatus` lista con búsqueda/orden/página; `GET /api/estatus/opciones` lista opciones activas.
- `GET/PUT /api/estatus/{id}`, `POST /api/estatus`, `PATCH /api/estatus/{id}/desactivar` y `/reactivar`; no existe borrado físico.
- `GET/POST /api/vehiculos`, `GET/PUT /api/vehiculos/{id}`, `GET /api/vehiculos/verificar-placa`, `PATCH /api/vehiculos/{id}/eliminar` y `/restaurar`, `GET /api/clientes/{id}/vehiculos`.

### Verificación final

- `.venv/bin/python -m py_compile` para módulos tocados: sin errores.
- `.venv/bin/python -m pytest -q backend/tests`: **137 passed** (suite completa, con acceso a MySQL local).
- Navegador con sesión: estatus, suspender/reactivar, abrir/cerrar edición por Escape, autocompletar marca/modelo, placa normalizada/disponible, registrar vehículo, conservar cliente y enfocar placa al registrar otro, y eliminar vehículo: comprobados. Se usó una fila de prueba y se dejó eliminada lógicamente; no se borró físicamente.
- Servidor estático limitado a `index.html` y `frontend/`: `/` y `/frontend/` dieron 200; `/.env`, `/backend/` y `/.git/` dieron 404. Servidor estático y API temporal detenidos; puertos 43257 y 5001 comprobados libres. `frontend/config.js` quedó restaurado a su destino local habitual (puerto 5000).
- La API temporal se configuró para aceptar solo el origen efímero del servidor; CORS no se abrió a `*`. Para otro origen local persistente, la lista de orígenes del despliegue debe configurarse sin ampliar permisos indiscriminadamente.

**Pendiente:** edición de cliente con persistencia/concurrencia probada, edición de vehículo, consulta de ficha y acciones completas, buscador por todos los campos, restauración/filtros de eliminados, avisos de validación junto a los campos, bloqueo por uso del catálogo, enlace retroactivo, paginación común de talleres y revisión integral de accesibilidad/roles en todas las pantallas. No se declaran terminadas esas capacidades hasta probar su ciclo funcional.
