# Fase 02 · Registro de clientes

## Análisis previo

1. El login original de `index.html` era demostrativo y no autenticaba contra el backend.
2. No existían sesión, roles persistidos, guard de rutas ni vínculo del usuario con un taller.
3. El proyecto ya establece MySQL en `.env.example`; se conserva ese motor y se añadió configuración Flask/MySQL.
4. El login ahora consulta `/api/auth/login`; la API firma una cookie de sesión con usuario, rol y taller. La vista de login actual carga en navegador; la autenticación contra MySQL queda pendiente de configuración.
5. `.env` no está disponible; la autenticación y persistencia no se pudieron probar contra la base local.

## Arquitectura y módulos

Flujo del registro: **Vista Vue → ClienteFacade frontend → ClienteRepository frontend → API REST Flask → ClienteFacade backend → ClienteRepository backend → MySQL**. El Repository backend ejecuta SQL parametrizado. El formulario nunca accede directamente a la API. Al registrar una fotografía, el navegador envía datos y foto en un multipart; el backend inserta la fila, mueve la foto dentro de la transacción y confirma. Si hay error, hace rollback y elimina el archivo.

| Actividad | Estado (Realizada/Pendiente/Verificada) | Observaciones |
|---|---|---|
| Login contra servicio | Realizada | `AuthFacade` llama a `/api/auth/login`; contraseña se verifica con bcrypt, se establece sesión firmada. La conexión real no se pudo probar. |
| Alta administrativa de usuarios | Realizada | `backend/manage_users.py` solicita contraseña interactivamente y guarda solo hash bcrypt; requiere MySQL configurado y taller existente. |
| Guard de rol y taller en backend | Realizada | Rutas protegidas comprueban sesión, `usuario_id`, taller y rol administrador/recepcionista; se admite `secretaria` por compatibilidad con los roles existentes solicitados anteriormente. |
| Visibilidad/guard de acceso del formulario | Realizada | Vue oculta el acceso a Clientes según el rol devuelto por sesión y comprueba el permiso antes de abrirlo. El backend es la autoridad final. |
| Formulario por secciones y validación inmediata | Realizada | Datos personales, contacto, fotografía y dirección; mensajes breves por campo, email/teléfonos/CP/edad y obligatorios. |
| Vista previa y validación de foto | Realizada | JPG/JPEG/PNG/WEBP, 15 MB máximo; frontend valida tipo/tamaño y backend extensión/firma/tamaño. |
| Facade y Repository frontend | Realizada | La Vista llama a `ClienteFacade`; su Repository transporta JSON/multipart y cookie de sesión. |
| API de clientes y duplicados | Realizada | POST 201, duplicados 409, inválidos 422, listado/consulta/PUT/foto/verificar duplicado. Restricciones UNIQUE cubren carreras concurrentes. |
| Transacción conjunta de cliente y foto | Realizada | `ClienteRepository.crear()` inserta, mueve archivo temporal y confirma; rollback elimina la foto final o temporal. Falta prueba integrada. |
| Esquema MySQL | Realizada | Migraciones `001_clientes.sql` y `002_usuarios_auth.sql`; aplicación en MySQL no verificada. |
| Dependencias Python en `.venv` | Pendiente | El intento de crear virtualenv falló: `ensurepip`/paquete `python3.13-venv` no está disponible; `sudo` requiere contraseña interactiva. |
| Pruebas reales de API y SELECT | Pendiente | No se ejecutaron; no hay `.env`, no están instaladas Flask/PyMySQL y MySQL denegó conexión sin configuración. No se simularon resultados. |
| Instalación/uso de Archify | Pendiente | `node`/`npx` están disponibles, pero la clonación del repositorio falló por conexión HTTPS a GitHub. Se dejó diagrama manual HTML autónomo más SVG. |
| Commit | Verificada | Commit local `Completa registro de clientes fase 2` creado. |
| Push no forzado | Pendiente | `git push -u origin master` quedó sin respuesta durante 30 segundos y se interrumpió; el remoto no confirmó publicación. No se usó force. |

**Usuarios y contraseñas:** no hay cuentas configuradas en el repositorio ni usuarios comprobados en MySQL; por tanto, no existen credenciales de acceso funcionales que pueda entregarte. No reutilices credenciales de la base de datos como acceso de aplicación. Para crear cuentas cuando MySQL esté disponible, ejecuta `python backend/manage_users.py` desde la raíz: solicita nombre, correo, rol, taller y contraseña; guarda bcrypt y no incluye la contraseña en archivos. El script limita roles de alta a administrador y recepcionista.

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
| `connect()` | Infraestructura datos | Abre PyMySQL con DB_HOST/PORT/NAME/USER/PASSWORD y autocommit desactivado. | Conexión. |
| `POST /api/clientes` | `crear_cliente` | Acepta JSON o multipart con `cliente` JSON y `foto` opcional. Taller/usuario salen de sesión. | `201`, `409`, `422`, `401/403`. |
| `GET /api/clientes` | `listar_clientes` | Filtros opcionales por nombre/email/teléfono; taller se toma de sesión. | `200 {clientes}`. |
| `GET /api/clientes/{id}` | `consultar_cliente` | ID dentro del taller activo. | `200` o `404`. |
| `PUT /api/clientes/{id}` | `actualizar_cliente` | Valida cuerpo completo y actualiza dentro del taller. | `200/404/409/422`. |
| `POST /api/clientes/{id}/foto` | `subir_foto` | Carga independiente para cliente existente; comprueba extensión/firma/tamaño y ruta. | `201/404/422`. |
| `GET /api/clientes/verificar-duplicado` | `verificar_duplicado` | Revisa email, teléfono y nombre+fecha en taller activo. | `200 {duplicado}`. |

## Datos y migraciones

`001_clientes.sql` crea `empresas`, `talleres` (FK a empresas) y `clientes`. `clientes`: `id`, `taller_id`, `nombre_completo`, `contacto_alterno`, `edad`, `fecha_nacimiento`, `telefono_personal`, `telefono_trabajo`, `email`, `email_trabajo NULL`, `foto_ruta NULL`, `calle`, `colonia`, `municipio`, `estado`, `codigo_postal`, `creado_por`, `created_at`, `updated_at`. Incluye índices en taller/email/teléfono; UNIQUE por taller en email, teléfono y nombre+fecha; FK de taller a talleres.

`002_usuarios_auth.sql` crea `usuarios` con taller, nombre, email UNIQUE, `password_hash`, rol, activo y timestamps; password hash es bcrypt. `creado_por` no tiene FK a usuarios en 001 por el orden de migración/tipo previo; queda por añadir una FK revisada tras migrar 002.

### Arranque local

1. Python 3.10+ y MySQL/MariaDB. Crea una base y prepara `.env` local a partir de `.env.example`; esta aplicación no lee credenciales desde el frontend.
2. Crea el entorno virtual: `python3 -m venv .venv`, actívalo y ejecuta `pip install -r backend/requirements.txt`.
3. Aplica, en orden, `backend/migrations/001_clientes.sql` y `backend/migrations/002_usuarios_auth.sql` a `DB_NAME`.
4. Crea una empresa y taller asociados. Crea cuentas con `python backend/manage_users.py` (correo único, rol y taller existentes; escribe la contraseña en el prompt oculto).
5. Inicia la API: `python backend/app.py`. Localmente escucha `APP_HOST` (127.0.0.1) y `APP_PORT` (5000). Sirve el frontend estático con `python3 -m http.server 4173 --bind 127.0.0.1`.
6. `frontend/config.js` apunta la API local. Ajusta `CORS_ORIGIN` al origen exacto del navegador y usa `SESSION_COOKIE_SECURE=true` bajo HTTPS.

## Diagrama de componentes

[HTML autónomo](docs/diagramas/fase-02-componentes-registro-clientes.html) (SVG inline, sin dependencias externas) · [Exportación SVG](docs/diagramas/fase-02-componentes-registro-clientes.svg). El HTML permite descargar el SVG.

Archify se intentó con el comando solicitado. No se pudo clonar su repositorio: `Failed to connect to github.com port 443`. Node v20.19.2 y npx v9.2.0 sí están disponibles; el diagrama alternativo se creó a mano usando los archivos implementados.

## Resultado real de pruebas

| Prueba | Resultado observado |
|---|---|
| Compilación sintáctica Python (`python3 -m py_compile backend/*.py`) | Verificada | Ejecutada tras los cambios actuales; terminó sin errores. |
| Carga de login actual en navegador (`http://127.0.0.1:4173/`) | Verificada | Se visualizó el formulario de ingreso y sus controles. No se envió login porque no hay cuenta de aplicación confirmada. |
| `POST` válido y `SELECT clientes` | Pendiente | `.env` no está presente; no se creó/inspeccionó/modificó. |
| Repetir mismos datos (409, sin nueva fila) | Pendiente | MySQL no pudo autenticar sin configuración local. |
| Formato inválido (422) | Pendiente | No ejecutada contra API. |
| Foto >15 MB/extensión o firma inválida | Pendiente | No ejecutada contra API. |
| Rol sin permiso (403) | Pendiente | No ejecutada contra API; guard implementado. |
| Iniciar entorno virtual e instalar dependencias | No completada: Python informó que `ensurepip` falta; instalar `python3.13-venv` requiere contraseña sudo interactiva. |
| Ping MySQL sin `.env` | Falló: `Access denied for user 'ady'@'localhost'`. No se hizo SELECT ni se inventaron datos. |
| Instalar Archify | Falló: sin conexión a `github.com:443`; se conservó alternativa manual. |

| Diagrama HTML actualizado y SVG abierto en navegador | Verificada | HTML autocontenido con SVG inline, sin dependencias externas; muestra componentes implementados, incluidas cuentas y autenticación. |

## Seguridad de contraseñas

Las contraseñas de cuentas se reciben mediante prompt oculto y se almacenan como hash bcrypt; el login compara el hash y no devuelve este dato. No hay usuarios de aplicación confirmados ni contraseñas funcionales disponibles. Tras configurar MySQL y crear empresa/taller, `python backend/manage_users.py` permite crear un usuario administrador o recepcionista y elegir su contraseña interactivamente. Recomendado antes de producción: definir `APP_SECRET_KEY` aleatoria fuera del repositorio, HTTPS y cookies `Secure`, limitar intentos de login, protección CSRF según el flujo de cookies, recuperación con token aleatorio de un solo uso y expiración, y cambiar inmediatamente cualquier contraseña provisional. Nunca reutilizar credenciales de MySQL como credenciales de usuario.

El HTML del diagrama es autocontenido y el SVG es un archivo independiente. Persistencia, login real y pruebas HTTP permanecen **pendientes de configuración local**. No se agregan credenciales predeterminadas al código.
