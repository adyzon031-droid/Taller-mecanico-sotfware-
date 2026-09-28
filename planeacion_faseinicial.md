# Planeación de la fase inicial · Gestión de taller mecánico

## Resumen

El repositorio contiene una interfaz de demostración en un único archivo, `index.html`. Usa Vue 3 desde CDN para el estado y las vistas, Tailwind CSS y Bootstrap desde CDN para estilos. Presenta un acceso, recuperación de contraseña simulada y un panel con indicadores, órdenes y actividad cargados desde datos escritos en el propio archivo.

La fase inicial **no cuenta con un backend ni con una conexión real a MySQL**. El formulario de acceso acepta los datos ingresados sin validarlos contra usuarios; la recuperación solo muestra un mensaje genérico. Los registros visibles son ejemplos estáticos, no datos guardados. Por esta razón, la autenticación, la autorización por rol y la persistencia se encuentran en progreso.

## Módulos y datos

| Módulo | Datos | Estado | Solución |
|---|---|---|---|
| Acceso visual | Correo y contraseña introducidos en el navegador; no se persisten | En progreso | Formulario Vue disponible. `login()` cambia a la vista principal sin validar credenciales. Falta endpoint de autenticación, sesión segura y manejo real de errores. |
| Recuperación de contraseña | Correo introducido en el navegador | En progreso | `sendRecovery()` presenta una confirmación genérica. No envía correo ni crea tokens o hashes. Falta flujo de recuperación de extremo a extremo. |
| Resumen del taller | Contadores y actividad definidos en `index.html` | En progreso | Panel visual con datos de muestra. Falta obtener datos de una API. |
| Órdenes de trabajo | Identificador, fecha, vehículo, placas, cliente, técnico y estado (arreglo estático `orders`) | En progreso | Tabla de órdenes recientes de demostración. No hay alta, edición, seguimiento persistente ni entidad en BD. |
| Clientes | Nombres incluidos en órdenes de muestra | En progreso | Se muestran como texto. No existe gestión ni tabla de clientes. |
| Vehículos | Marca/modelo y placas incluidos en órdenes de muestra | En progreso | Se muestran como texto. No hay catálogo ni relación persistente con clientes. |
| Usuarios y roles | Nombre/rol de demostración (“Andrea Morales”, “Administradora”) | En progreso | Perfil visual estático. No hay cuentas, roles almacenados ni autorización. Admin, Gerente, Secretaria, Técnico y Cliente son requisitos, no funciones implementadas. |
| Notificaciones | Indicador visual en la barra superior | En progreso | Icono decorativo; no hay bandeja ni notificaciones generadas. |
| Persistencia MySQL | Ninguno | En progreso | No hay backend, esquema, migraciones ni conexión. No existe ninguna tabla o modelo implementado. |
| Reportes y configuración | Enlaces de navegación visuales | En progreso | No hay páginas ni acciones asociadas. |

**Datos/tablas implementados:** ninguno. Los arreglos `orders` y `jobs` son datos temporales JavaScript, no tablas ni modelos. El diseño de las entidades y sus relaciones queda **PENDIENTE**.

## Documentación del código

### Archivo existente

- `index.html`: documento completo de la interfaz. Incluye la estructura HTML, estilos CSS, dependencias por CDN y la aplicación Vue.

### Funciones y estado Vue

La aplicación se inicializa con `createApp(...).mount('#app')`.

- `data()`: define el estado de la pantalla (autenticación simulada, correo, contraseña, recuperación y aviso de nueva orden), además de los arreglos de muestra `orders` y `jobs`.
- `login()`: limpia el mensaje de error y cambia `authenticated` a `true` si los campos requeridos están presentes. **No autentica** ni consulta una API.
- `sendRecovery()`: valida que se haya escrito un correo y activa `sent` para mostrar un mensaje. **No envía correo**, no verifica que la cuenta exista y no genera hash, token ni enlace.
- `showPassword`, `recovering` y `newOrder`: controlan interacciones visuales en el navegador. El aviso de nueva orden dice que el formulario corresponderá a una fase posterior.

### Endpoints, modelos y tablas

No existen rutas HTTP de backend, controladores, servicios, modelos ORM, validaciones de servidor ni esquema SQL en este repositorio. En consecuencia, no hay endpoints que documentar; definirlos queda **PENDIENTE** junto con la selección de tecnología de backend.

## Conexión a la base de datos

No se encontró código de conexión a MySQL ni un archivo de configuración que lo consuma. La base local mencionada por el propietario no está conectada desde esta aplicación. Sus valores de acceso no se incluyen aquí ni se deben agregar al repositorio.

La plantilla `.env.example` enumera variables sugeridas para el backend futuro. `.env` está excluido mediante `.gitignore` y no existe en el proyecto. En un backend implementado, este leería `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` del entorno al inicializar su cliente MySQL. `APP_PORT` define el puerto del servicio y `CORS_ORIGIN`/`FRONTEND_URL` restringirían el origen web permitido. Hoy estas variables son solo una referencia: **ningún programa las lee**. El nombre de la base, el cliente/librería MySQL y el formato de migraciones están **PENDIENTES**.

## Guía de publicación (frontend y backend)

### Frontend actual

Requisitos: repositorio GitHub y una cuenta en un hosting de sitios estáticos (por ejemplo, GitHub Pages, Netlify o Cloudflare Pages). No requiere compilación ni Node.js en el estado actual; el navegador descarga Vue, Tailwind y Bootstrap desde sus CDN, por lo que necesita acceso a internet.

1. Publica el repositorio en GitHub (véase el estado de publicación al final de esta guía).
2. En el proveedor elegido, importa el repositorio y selecciona la rama publicada.
3. Configura la raíz del proyecto como directorio de publicación. No indiques comando de build; publica `index.html` directamente.
4. Guarda el dominio asignado y abre la URL. Comprueba la pantalla de acceso y la vista de demostración.

No configures credenciales MySQL en el hosting del frontend. Los archivos enviados al navegador son públicos. Cuando exista una API, se podrá definir una variable pública como `VITE_API_BASE_URL` durante la compilación, pero el frontend actual no utiliza Vite ni lee esa variable.

### Backend y MySQL (pendiente de implementación)

No hay backend que se pueda desplegar actualmente. Antes de publicarlo se necesita **PENDIENTE**: elegir lenguaje/framework y versión, implementar API y autenticación/autorización, definir esquema y migraciones MySQL, administrar CORS, y agregar instrucciones reproducibles (por ejemplo, `package.json`/`requirements.txt` y un comando de inicio). La ausencia de estos elementos impide dar comandos de build o start que funcionen hoy.

Cuando esos elementos estén implementados:

1. Crear un servicio de backend en un proveedor que soporte el runtime elegido (por ejemplo, Render o Railway), enlazado con la rama publicada. Configurar el comando de build/inicio real del proyecto; ahora está **PENDIENTE**.
2. Crear una instancia MySQL accesible desde ese servicio. `localhost` solo apunta al mismo equipo/contenedor del proceso; para alojamiento remoto se debe usar el host que entregue la instancia de MySQL y permitir la conexión desde el backend.
3. En el panel privado del proveedor, definir `APP_PORT` (si el proveedor no lo inyecta), `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `CORS_ORIGIN` y `FRONTEND_URL`. No subir `.env` ni copiar secretos a variables compiladas dentro del frontend.
4. Aplicar las migraciones documentadas y verificar el estado del servicio y la conexión a MySQL usando los procedimientos de salud que se implementen (**PENDIENTE**).
5. Configurar `CORS_ORIGIN` con el dominio HTTPS exacto del frontend y actualizar `FRONTEND_URL`. Probar el flujo completo desde la URL publicada.

No existe un comando de despliegue del backend que pueda ejecutarse en esta fase: faltan el backend y sus dependencias. La publicación del frontend puede ser independiente y mostrará solamente la demostración estática.

### Publicación del repositorio en GitHub

El repositorio local tiene configurado un remoto llamado `origin` con URL GitHub y una rama local `master`. El acceso de red a GitHub no pudo verificarse durante esta tarea, por lo que el estado remoto queda **PENDIENTE de confirmación**. Los cambios de este documento y de la protección de secretos deben confirmarse antes de publicar:

```bash
git status --short
git add .gitignore .env.example planeacion_faseinicial.md
git diff --cached
git commit -m "Documenta la planeación de la fase inicial"
git push -u origin master
```

Antes del commit, revisa `git diff --cached` para confirmar que no incluya `.env` ni datos reales. Si GitHub rechaza el push por permisos o porque la rama predeterminada es distinta, configura el acceso y sincroniza la rama según las instrucciones del repositorio; no sustituyas esa revisión por publicar un secreto.

## Pendientes

- Implementar el backend y seleccionar su tecnología, estructura, endpoints y estrategia de despliegue.
- Definir entidades y tablas MySQL: usuarios, roles/permisos, clientes, vehículos, órdenes, trabajos/servicios y notificaciones; acordar claves, relaciones, restricciones y migraciones. Esta lista es una propuesta por validar, no un esquema existente.
- Implementar autenticación real y autorización del lado servidor para Admin, Gerente, Secretaria, Técnico y Cliente. Aplicar mínimo privilegio y comprobar el acceso del cliente únicamente a sus vehículos y notificaciones.
- Para contraseñas, guardar únicamente hashes adaptativos modernos (Argon2id recomendado; bcrypt como alternativa compatible), con sal única por contraseña gestionada por la librería. No usar SHA-256/MD5 simples ni cifrado reversible. Aplicar límites a intentos de acceso y respuestas que no revelen si un correo está registrado.
- Diseñar recuperación con tokens aleatorios de un solo uso, expiración corta y almacenamiento del hash del token; nunca guardar ni enviar contraseñas. Invalidar sesiones según la política acordada.
- Implementar API, persistencia, validaciones, manejo de errores y pruebas; sustituir los arreglos de demostración por datos autorizados del servidor.
- Determinar nombre de base, proveedor de MySQL, correo transaccional para recuperación, dominios, variables definitivas, política de respaldos y monitoreo.
- Verificar y completar la publicación GitHub: el remoto está configurado localmente, pero el acceso remoto y el push no quedaron confirmados en esta documentación.
