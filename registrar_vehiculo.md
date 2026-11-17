# Registro de vehículos · Torque

**Alcance documentado:** implementación de registro y gestión inicial de vehículos en la BD local. La solicitud nombró `registrar_vehiculo.mdb`; se usa `.md` por tratarse de documentación Markdown. No se incluyen secretos ni datos identificables.

## Estado por fase

| Fase | Actividad | Estado | Observaciones |
|---|---|---|---|
| Datos | Crear `vehiculos`, claves foráneas, estatus y claves de unicidad vigentes | Verificada | Migración `backend/migrations/012_estatus_clientes_vehiculos.sql` aplicada y repetida; se conservan filas al eliminar. |
| Backend | Validar, registrar, consultar, editar y dar de baja/restaurar | Verificada parcialmente | Facade y Repository implementados. Se verificaron pytest y un ciclo de alta/baja desde navegador; edición y restauración quedan pendientes de recorrido completo. |
| Catálogo | Autocompletar marcas/modelos y permitir propuesta manual pendiente | Verificada parcialmente | Sugerencias corregidas y comprobadas en navegador. El backend crea propuestas en espera dentro de la transacción de alta. El bloqueo de desactivación por uso necesita verificación adicional. |
| Interfaz | Registro con cliente fijado, placa normalizada y opción para registrar otro | Verificada | Alta HTTP 201 observada; “Registrar otro” conservó cliente y enfocó placa. |
| Pruebas | Suite automatizada y recorrido de navegador | Verificada parcialmente | `137 passed`; el navegador verificó alta y baja. No se declara cobertura visual completa de todos los flujos. |

## Precondiciones

- Migraciones previas del sistema aplicadas y conexión a MariaDB configurada mediante el entorno local existente. No se muestran valores de configuración.
- Sesión autenticada y taller activo. El backend toma `taller_id` desde la sesión; no se confía en un taller enviado por el cliente.
- Cliente activo asociado al mismo taller. Marca/modelo pueden seleccionarse del catálogo o proponerse como valores pendientes.
- La tabla `estatus` contiene los valores de esta fase y conserva sus identificadores legados.

## Datos y reglas

La tabla `vehiculos` conserva `taller_id`, `cliente_id`, `estatus_id`, datos de catálogo/texto de marca y modelo, placa, serie/VIN, año, kilometraje, fecha de alta/compra, timestamps y metadatos de eliminación lógica. Sus identificadores de relación usan `BIGINT UNSIGNED`, igual que las tablas referenciadas. Las columnas `placa_vigente` y `serie_vigente` mantienen la unicidad de filas activas; al eliminar se ponen en `NULL` para permitir una nueva alta con el mismo valor sin borrar el historial.

| Campo | Regla implementada | Estado |
|---|---|---|
| Placa | Requerida; se normaliza a mayúsculas y se retiran separadores para comparación. La interfaz muestra una vista previa normalizada. | Verificada en navegador con placa de prueba. La expresión concreta se valida en `VehiculoFacade.validate`; no se replica aquí para evitar divergencia. |
| Cliente | ID requerido; debe existir, estar activo y pertenecer al taller de sesión. | Verificación automatizada; no se exponen identificadores reales. |
| Marca/modelo | Selección del catálogo o texto manual; el modelo debe corresponder a la marca. La propuesta manual se crea pendiente en la misma transacción. | Autocomplete verificado; validación backend incluida. |
| Año y kilometraje | Rangos, coherencia de fecha y advertencias de kilometraje se validan en Facade. | Suite automatizada; mensajes en campo no verificados integralmente en el navegador. |
| Serie/VIN | Validación de formato; dígito verificador inválido se trata como advertencia cuando aplica. | Suite automatizada. |
| Estado | Se crea con estatus `activo`; la baja cambia a `eliminado`, conserva la fila y registra autor/fecha. | Alta y baja lógica verificadas. |

Las reglas de entrada tienen una implementación principal en `backend/vehiculo_facade.py` (`VehiculoFacade.validate`) y una validación previa en `frontend/vehiculos/vehiculoFacade.js`. El backend es la autoridad. Errores de campo se responden como `422` con `errors`; duplicados/conflictos como `409`; falta de permiso como `403`; objetos ajenos al taller como `404`. Las advertencias de validación se devuelven en `warnings`; su presentación junto al campo está pendiente de verificación/terminación.

## Flujo de datos

`Vista Vue → VehiculoFacade (frontend) → VehiculoRepository (frontend) → API Flask → VehiculoFacade (backend) → VehiculoRepository (backend) → MariaDB`.

La vista usa la Facade. Solo el Repository frontend llama la API y solo el Repository backend ejecuta SQL. Las consultas y escrituras de vehículos se limitan al taller de sesión. El registro crea vehículo y posibles marca/modelo pendientes dentro de una transacción. La baja es lógica; no se elimina físicamente la fila.

## Endpoints

| Método y ruta | Función | Respuestas relevantes |
|---|---|---|
| `GET /api/vehiculos` | Lista vehículos del taller con filtro/paginación disponibles. | `200`, `401/403` |
| `POST /api/vehiculos` | Registra vehículo; puede crear elementos de catálogo pendientes en la misma transacción. | `201`, `409`, `422` |
| `GET /api/vehiculos/{id}` | Consulta ficha dentro del taller de sesión. | `200`, `404` |
| `PUT /api/vehiculos/{id}` | Actualiza vehículo existente del taller. | `200`, `404`, `409`, `422` |
| `GET /api/vehiculos/verificar-placa?placa=…` | Comprueba disponibilidad de placa en el taller. | `200` |
| `GET /api/clientes/{id}/vehiculos` | Lista vehículos del cliente dentro del taller. | `200`, `404` |
| `PATCH /api/vehiculos/{id}/eliminar` | Baja lógica. | `200`, `404` |
| `PATCH /api/vehiculos/{id}/restaurar` | Restaura registro; se reserva al rol autorizado por la ruta. | `200`, `403`, `404`, `409` |

## Métodos y funciones

| Nombre | Capa | Propósito | Parámetros → retorno |
|---|---|---|---|
| `VehiculoFacade.validate(data, today=None)` | Backend, dominio | Normaliza/valida campos y prepara errores/advertencias. | Objeto y fecha opcional → datos validados o `VehicleError`. |
| `VehiculoFacade.create(user, data)` | Backend, dominio | Coordina validación y creación. | Usuario de sesión y datos → vehículo/advertencias o error de dominio. |
| `VehiculoRepository._scope(user)` | Backend, persistencia | Obtiene el alcance de taller desde sesión. | Usuario → `taller_id`. |
| `VehiculoRepository.list(user, args, include_deleted=False)` | Backend, persistencia | Lista registros dentro del taller y aplica filtros/página. | Usuario, parámetros y bandera → elementos y metadatos. |
| `VehiculoRepository.get(user, record_id)` | Backend, persistencia | Obtiene el vehículo visible para el taller. | Usuario e ID → objeto o ausencia. |
| `VehiculoRepository.verify_plate(user, plate, exclude=None)` | Backend, persistencia | Comprueba placa vigente sin revelar vehículos de otro taller. | Usuario, placa y exclusión opcional → disponibilidad. |
| `VehiculoRepository.create(user, data)` | Backend, persistencia | Inserta en transacción, enlaza catálogo o crea propuestas pendientes. | Usuario y datos validados → ID/registro; rollback ante error. |
| `VehiculoRepository.update(user, record_id, data)` | Backend, persistencia | Actualiza un vehículo del taller. | Usuario, ID y datos → registro actualizado o error. |
| `VehiculoRepository.change_deleted(user, record_id, restore=False)` | Backend, persistencia | Marca eliminado o restaura; conserva la fila y valida unicidad. | Usuario, ID, bandera → resultado del cambio. |
| `VehiculoRepository.by_client(user, client_id)` | Backend, persistencia | Lista vehículos asociados a cliente en el taller. | Usuario e ID cliente → lista. |
| `VehiculoFacade.normalizarPlaca(value)` | Frontend, Facade | Retira guiones/espacios y normaliza mayúsculas. | Texto → placa normalizada. |
| `VehiculoFacade.validar(data)` | Frontend, Facade | Valida placa, marca, año y fecha requeridos para la vista. | Datos → mapa de errores. |
| `VehiculoFacade.listar(params)`, `registrar(data)`, `actualizar(id,data)` | Frontend, Facade | Coordina consulta, validación y alta/edición. | Parámetros o datos → promesa de `VehiculoRepository`. |
| `VehiculoFacade.verificarPlaca(plate,exclude)`, `porCliente(id)`, `eliminar(id)`, `restaurar(id)` | Frontend, Facade | Coordina verificación de placa, consulta por cliente y estado lógico. | Placa/IDs → promesa de `VehiculoRepository`. |
| `VehiculoRepository.request(path,options)` | Frontend, Repository | Hace fetch con cookie de sesión y convierte respuestas fallidas a Error. | Ruta/opciones → JSON o Error con status/errors. |
| `VehiculoRepository.list`, `save`, `get`, `update`, `verifyPlate`, `byClient`, `remove`, `restore` | Frontend, Repository | Mapea cada operación a su endpoint HTTP. | Parámetros/IDs → promesa JSON. |
| `vehiculoAutocomplete.js` | Frontend, componente | Busca y presenta sugerencias de marca/modelo; permite elegir propuesta manual. | Texto/eventos → opción elegida para la Facade. |

## Verificación ejecutada

- `python -m py_compile` sobre los módulos backend tocados: sin errores (ejecutado mediante `.venv/bin/python`).
- `.venv/bin/python -m pytest -q backend/tests`: **137 passed** con acceso a MySQL local.
- Navegador: autocomplete de marca/modelo, normalización y verificación de placa, alta `201`, “Registrar otro” conservó cliente/enfocó placa y baja lógica confirmada. Se dejó un registro de prueba eliminado lógicamente; no se borró físicamente.
- Se verificó que el conteo agregado de vehículos fuera 1 total, 0 activos y 1 eliminado; no se imprimieron datos personales.
- Servidor estático temporal limitado a `index.html` y `frontend/`: recursos esperados `200`; `/.env`, `/backend/` y `/.git/` respondieron `404`. Ambos servidores temporales fueron detenidos y los puertos quedaron libres.

## Pendientes

- Probar edición, ficha y restauración con sesión de navegador.
- Completar/verificar listado con búsqueda por todos los campos, filtro de eliminados y menú accesible de acciones.
- Mostrar errores y advertencias bajo sus respectivos campos; terminar la comprobación de doble envío, foco atrapado y cierre con Escape para cada modal.
- Verificar conteo de uso y bloqueo de desactivación de marcas/modelos vinculados, enlace retroactivo de vehículos preexistentes y todas las combinaciones de catálogo contra BD real.
- Revisar la integración paginada de talleres y uniformar metadatos del helper en todos los endpoints administrativos.

## Relaciones e historial de vehículos

| UC | Nombre | Estado | Evidencia | Observaciones |
|---|---|---|---|---|
| UC-CV-10 | Detectar vehículo duplicado | Parcial | Migración 013 y `VehiculoRepository.create` | Backend implementado; falta recorrido visual y pruebas específicas. |
| UC-CV-11 | Asociar vehículo a cliente | Parcial | `cliente_vehiculo` y `POST /api/vehiculos/{id}/relaciones` | Backend implementado; falta interfaz y pruebas específicas. |
| UC-CV-12 | Cambiar propietario | Parcial | `VehiculoRepository.cambiar_propietario` | Backend implementado; falta interfaz y pruebas específicas. |
| UC-CV-13 | Consultar vehículos de un cliente | Parcial | `VehiculoRepository.by_client` | Backend implementado; falta presentación de históricos. |

`cliente_vehiculo` conserva cliente, vehículo, taller, tipo, vigencia, motivo y cierre. `auditoria` conserva eventos de relaciones y excepciones, solo permite inserciones y se indexa por entidad y taller.

| Ruta | Propósito |
|---|---|
| `GET/POST /api/vehiculos/{id}/relaciones` | Consulta asociaciones y registra una asociación. |
| `POST /api/vehiculos/{id}/cambiar-propietario` | Cierra el propietario vigente, crea el nuevo y actualiza `vehiculos.cliente_id`. |
| `GET /api/clientes/{id}/vehiculos` | Lista relaciones vigentes; `incluir_historicos=1` incorpora cerradas. |

| Método | Capa | Propósito |
|---|---|---|
| `VehiculoFacade.validar_relacion` | Backend | Valida cliente, tipo, fecha y motivo. |
| `VehiculoRepository.asociar` | Backend | Inserta relación y auditoría. |
| `VehiculoRepository.cambiar_propietario` | Backend | Cambia propietario con bloqueo y transacción. |
| `VehiculoRepository.relaciones` | Backend | Consulta el historial de un vehículo. |
