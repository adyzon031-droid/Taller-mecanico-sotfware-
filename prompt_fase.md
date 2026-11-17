
CONTEXTO
Sistema "Torque · Taller mecánico" (Vue → Facade → Repository → API Flask → MariaDB 11, multi-taller). La especificación es el documento "Fase_1_Gestion_Clientes_Vehiculos_Taller_Mecanico" con casos de uso UC-CV-xx (flujo, regla, resultado). Debo cumplir cada UC-CV, pero NO rehacer lo que ya está hecho. Lee solo lo necesario, inspecciona el esquema real, reutiliza lo existente (estatus, paginación del backend, modales, íconos, notificaciones, validadores, normalización) y respeta Vista → Facade → Repository. No modifiques ni imprimas .env.

REGLAS
- No uses git (add, commit, push, stash, reset).
- Documentación solo la indicada en la TAREA 5. No imprimas datos personales ni contraseñas.
- Validaciones iguales en frontend y backend; el backend es la autoridad. Errores 422, duplicados y conflictos 409, sin permiso 403, recurso de otro taller 404.
- Migraciones idempotentes, no destructivas, con el siguiente número disponible. Nunca borres físicamente datos: todo se cierra o se desactiva.
- Ante una ambigüedad, asume lo más coherente con el código existente y decláralo en una línea al final.

TAREA 0: LOCALIZAR LA ESPECIFICACIÓN E INVENTARIAR (obligatoria, antes de escribir código)
- Busca el texto de los UC-CV en el repositorio (planeacion_faseinicial.md, Fase_02.md, registrar_vehiculo.md, docs/, y cualquier .docx o .doc; si hay un Word, léelo con python-docx o conviértelo a texto). Para los casos cuyo texto no encuentres, no inventes: lístalos como "no leídos" al final.
- Clasifica TODOS los UC-CV que encuentres con evidencia concreta en una tabla: | UC | Nombre | Estado | Evidencia (archivo:función, endpoint, pantalla, prueba) | Qué falta |.
  - Hecho: existe el código, el endpoint o la pantalla, y una prueba que lo demuestre. No toques su código; solo ejecuta sus pruebas existentes.
  - Parcial: existe una parte. Implementa únicamente lo que falta.
  - Pendiente: no existe. Impleméntalo completo.
  Sin evidencia, un caso no cuenta como Hecho.
- La tabla va al inicio de tu respuesta final.

TAREA 1: UC-CV-10 · DETECTAR VEHÍCULO DUPLICADO (solo si no está hecho)
- Flujo: VIN exacto + placa y atributos como señales secundarias → alerta. Regla: un VIN duplicado activo dentro del mismo taller se bloquea, salvo excepción auditada. Resultado: bloqueo o alerta.
- VIN: al crear o editar un vehículo, el backend busca otro vehículo activo (no eliminado) con el mismo VIN en el mismo taller. Si existe responde 409 con un código identificable (por ejemplo VIN_DUPLICADO), el id del vehículo en conflicto y un mensaje claro, sin datos personales de ningún cliente. VINs iguales en talleres distintos están permitidos, y el VIN de un vehículo eliminado puede reutilizarse.
- Excepción auditada: solo el administrador puede registrar el vehículo a pesar del duplicado, con un motivo obligatorio (mínimo 10 caracteres). Queda marcado con excepcion_auditada y se registra en auditoría con quién, cuándo, el motivo y el id del vehículo en conflicto. La recepcionista recibe 403 al intentarlo.
- Integridad: refuerza el bloqueo en la base de datos con una columna generada que vale NULL cuando el vehículo está eliminado o tiene excepcion_auditada, más UNIQUE (taller_id, esa columna), para que dos peticiones simultáneas no creen duplicados y la excepción siga siendo posible.
- Señales secundarias (alerta, no bloqueo): misma placa activa en el mismo taller, o coincidencia de marca, modelo y año con otro vehículo del mismo taller. La respuesta incluye posibles_duplicados (id, placa, marca, modelo, año, estatus; sin datos del propietario) y la pantalla muestra un aviso en ámbar con las opciones "Cancelar", "Es el mismo vehículo (abrir ficha)" y "Registrar de todos modos". Si el VIN coincide, el aviso es de bloqueo y solo el administrador ve "Registrar con excepción", que pide el motivo.

TAREA 2: UC-CV-11 · ASOCIAR VEHÍCULO A CLIENTE (solo si no está hecho)
- Flujo: cliente + vehículo → validar → relación → tipo/vigencia → auditar. Regla: soportar relaciones históricas; una relación principal vigente si la política lo establece. Resultado: relación activa.
- Tabla `cliente_vehiculo`: id, cliente_id FK, vehiculo_id FK, taller_id FK, tipo_relacion (propietario, conductor habitual o responsable de pago, como catálogo o ENUM extensible), es_principal, fecha_inicio, fecha_fin (NULL = vigente), motivo, created_by, created_at, cerrada_por, cerrada_en. Tipos de las FK idénticos a los de las tablas referenciadas, con ON DELETE RESTRICT, e índices por cliente, vehículo y vigencia.
- Política configurable como constante: un solo propietario principal vigente por vehículo. Refuérzala con una columna generada (vehiculo_id cuando es_principal y fecha_fin es NULL) y UNIQUE.
- Validaciones: cliente activo del mismo taller (suspendido o eliminado → 409), vehículo activo del mismo taller, y sin duplicar la misma relación vigente (cliente, vehículo y tipo) (409).
- Migración de datos: por cada vehículo existente crea la relación propietario principal vigente con su cliente actual (fecha_inicio = fecha de ingreso o de creación). Conserva vehiculos.cliente_id como copia del propietario principal vigente, actualizada en la misma transacción, pero no la uses como fuente de verdad en consultas nuevas.
- Endpoints: POST /api/vehiculos/{id}/relaciones (asociar), GET /api/vehiculos/{id}/relaciones (vigentes e históricas). Permisos: recepcionista y administrador. Toda asociación se registra en auditoría.

TAREA 3: UC-CV-12 · CAMBIAR PROPIETARIO/CLIENTE RELACIONADO (solo si no está hecho)
- Flujo: cerrar relación anterior → crear nueva → fecha/motivo → auditar. Regla: nunca eliminar una relación histórica con operaciones asociadas. Resultado: relación vigente correcta.
- Endpoint POST /api/vehiculos/{id}/cambiar-propietario { cliente_nuevo_id, fecha_efectiva, motivo }. En una sola transacción con bloqueo de la fila del vehículo (SELECT … FOR UPDATE): cierra la relación principal vigente (fecha_fin = fecha_efectiva, motivo, quién y cuándo), crea la nueva como propietario principal vigente y audita. Si algo falla, no queda nada a medias.
- Validaciones: fecha y motivo obligatorios (motivo de al menos 10 caracteres); fecha efectiva no futura y no anterior al inicio de la relación vigente; cliente nuevo activo, del mismo taller y distinto del actual (422); vehículo activo. Al terminar debe existir exactamente una relación principal vigente.
- Nunca se elimina una relación: no existe endpoint DELETE, las FK usan ON DELETE RESTRICT y un trigger BEFORE DELETE en cliente_vehiculo rechaza el borrado físico. Cambia también vehiculos.cliente_id en la misma transacción.
- Interfaz: acción "Cambiar propietario" en el menú "⋯" del vehículo y en su ficha, con modal: propietario actual, buscador del cliente nuevo (activos del taller), fecha efectiva (por defecto hoy), motivo obligatorio y resumen "De X → a Y" antes de confirmar. La ficha del vehículo muestra el historial de propietarios en línea de tiempo (desde, hasta, motivo).

TAREA 4: UC-CV-13 Y DEMÁS CASOS
- UC-CV-13 · Consultar vehículos de un cliente: sigue el flujo, la regla y el resultado del documento si los encuentras. Si no, implementa: GET /api/clientes/{id}/vehiculos con las relaciones vigentes por defecto, parámetro incluir_historicos para ver las cerradas, paginación del servidor, y por cada fila placa, marca, modelo, año, tipo de relación, si es principal, desde y hasta; solo clientes del taller de la sesión (otro taller → 404). Se muestra en la ventana "Vehículos" de Gestión de clientes y en la ficha del cliente, con un interruptor "Ver históricos". Decláralo si usaste la versión por defecto.
- Los demás UC-CV (01 al 09 y 14 en adelante): aplica el mismo criterio de la Tarea 0 y, si resultan Parcial o Pendiente, impleméntalos según su flujo, regla y resultado. No inventes los que no hayas podido leer.
- Auditoría compartida: si ya existe un mecanismo de auditoría, reutilízalo. Si no, crea la tabla `auditoria` (id, taller_id, usuario_id, entidad, entidad_id, accion, motivo, datos_antes y datos_despues en JSON sin datos personales ni contraseñas, created_at) con índices por (entidad, entidad_id) y (taller_id, created_at), solo de inserción (triggers que rechacen UPDATE y DELETE), y un helper que escriba dentro de la misma transacción que la operación auditada. Agrega GET /api/auditoria?entidad=&entidad_id= (solo administrador, paginado) para mostrar el historial en la ficha.

TAREA 5: PRUEBAS Y DOCUMENTACIÓN
- Antes de cambiar nada, ejecuta la suite completa y anota el total; al terminar vuelve a ejecutarla (que no baje) y muestra ambos totales reales.
- pytest solo para lo que implementes:
  - UC-CV-10: VIN duplicado en el mismo taller 409 con código; mismo VIN en otro taller permitido; VIN de un vehículo eliminado reutilizable; excepción como administrador con motivo (queda auditada) y sin motivo (422); recepcionista 403; placa o atributos repetidos solo dan alerta; dos creaciones simultáneas con el mismo VIN (solo una tiene éxito).
  - UC-CV-11: asociar con cliente suspendido 409, cliente de otro taller 404, relación vigente duplicada 409, segundo principal vigente rechazado, migración de datos existentes, consulta de históricas, auditoría creada.
  - UC-CV-12: cambio de propietario correcto (relación anterior cerrada, nueva vigente, una sola principal vigente), reversión completa si falla un paso, fecha futura o anterior al inicio 422, motivo faltante 422, mismo cliente 422, sin endpoint DELETE, un DELETE directo en SQL rechazado por el trigger.
  - UC-CV-13: vigentes por defecto, históricos con el interruptor, paginación, cliente de otro taller 404.
- En el navegador, con un servidor local temporal limitado a index.html y frontend/ en 127.0.0.1 (verifica que /.env, /backend/ y /.git/ den 404 y deténlo al terminar), prueba cada flujo implementado. Si el login no se completa en el servidor temporal, diagnostica la causa con evidencia (origen y puerto frente a CORS, cookies, URL de la API) sin abrir CORS a "*". Lo que no puedas probar, dilo en una línea y no simules resultados.
- Documentación (solo estos archivos): agrega a registrar_vehiculo.md (créalo si no existe) la tabla | UC | Nombre | Estado (Hecho, Realizado ahora, Pendiente o No leído) | Evidencia | Observaciones |, el esquema de las tablas nuevas, los endpoints y la descripción objetiva, clara y precisa de cada método y función nuevo (nombre, capa, propósito, parámetros, retorno). Marca "Verificado" solo lo realmente probado.

RESTRICCIONES
Responde solo con lo necesario: sin explicaciones extensas, sin repetir código existente. Empieza con la tabla de la Tarea 0, lista únicamente los archivos creados o modificados y el resultado real de cada prueba.
