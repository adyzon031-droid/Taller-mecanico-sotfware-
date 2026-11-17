---
name: skill-backend-python
description: Guía técnica del dominio backend para analizar, diseñar, implementar y validar servicios REST con Python, Flask y MariaDB mediante especificaciones verificables y alcance controlado. Lo gobierna orquestador-backend.md.
version: 1.1.0
language: es
---

# Skill profesional — Python, Flask y servicios RESTful

## 1. Propósito y contrato de aplicación

Actúa como ingeniero senior de Python. Desarrolla software mantenible, seguro y verificable aplicando Specification-Driven Development (SDD): especificar, diseñar la solución mínima suficiente, implementar y comprobar contra criterios de aceptación.

`orquestador-backend.md` gobierna su ejecución. **DEBE** indica obligación; **DEBERÍA**, recomendación con excepción justificada; **PUEDE**, opción condicionada al alcance. No crear funcionalidades adicionales bajo el argumento de aplicar buenas prácticas.

### Activación
Aplicar al crear o modificar endpoints, repositorios, migraciones, validaciones, seguridad, pruebas u optimizaciones del backend Flask/MariaDB.
No aplicar a interfaz (Vue) ni a errores del frontend: se enrutan a `frontend/`.

### Entradas mínimas
- Solicitud y resultado observable esperado.
- Estructura real del repositorio (`app.py`, repositorios, migraciones, pruebas).
- Versiones reales de Python, Flask, MariaDB y dependencias (`requirements.txt`).
- Contratos y consumidores afectados (el frontend consume el contrato existente).
- Restricciones de seguridad, multi-taller y compatibilidad.

Si falta un dato, distinguir supuesto reversible de decisión bloqueante. Nunca inventar acceso al repositorio, reglas de negocio ni resultados de pruebas.

### Salida para el frontend
En tareas mixtas entregar el contrato como artefacto: método, ruta, request, response, códigos de error, permisos y paginación. El frontend lo consume sin inventar endpoints ni propiedades.

## 2. Protocolo SPEC y trazabilidad

Toda modificación DEBE tener justificación rastreable: `REQ → AC → TASK → cambio → TEST/evidencia`.
Un hallazgo ajeno al alcance se registra como propuesta (`CR-xxx`); no se implementa.

### Plantilla mínima de especificación
```markdown
# SPEC: <ID y título>
Estado: borrador | lista | en ejecución | validada | bloqueada
Objetivo observable: <resultado>
Incluido: <lista cerrada>
Excluido: <lista explícita>
Restricciones: <compatibilidad, seguridad, multi-taller, datos>
Supuestos: <ID, fundamento, cómo validarlo>
REQ-001: <comportamiento verificable>
BR-001: <regla de negocio confirmada>
AC-001: Dado <contexto>, cuando <acción>, entonces <resultado>.
Contrato: <método, ruta, request, response, errores, permisos>
Datos: <tablas, integridad, transacciones, consultas>
TASK-001 → REQ-001 / AC-001: <cambio concreto y archivo>
TEST-001 → AC-001: <caso y evidencia esperada>
Riesgos y pendientes: <impacto y tratamiento>
```

## 3. Base tecnológica y dependencias

1. Inspeccionar `requirements.txt`, entorno virtual y `.env.example` antes de decidir versiones.
2. Conservar las versiones existentes; no actualizar versiones mayores sin alcance autorizado.
3. Añadir solo dependencias necesarias para un requisito, con versión fijada y registrada en la SPEC.
4. Configuración y secretos desde variables de entorno (`.env` fuera de Git); proveer `.env.example` sin valores reales.
5. Mantener el stack: Flask, PyMySQL (ya usado en el proyecto), pytest. No introducir ORM, framework asíncrono ni contenedores sin alcance autorizado.

## 4. Arquitectura proporcional

- Respetar la línea existente: **ruta (Flask) → servicio/fachada → repositorio → MariaDB**.
- Las rutas solo traducen HTTP: leen parámetros, llaman al caso de uso y construyen la respuesta. Sin SQL ni reglas de negocio en la ruta.
- Reglas de negocio y validaciones en funciones/servicios reutilizables; SQL solo en repositorios.
- Un repositorio por entidad (`cliente_repository.py`, etc.). No crear repositorios genéricos ni capas que solo repitan otra.
- Preferir funciones simples y composición; abstraer solo con una variación real que resolver.
- Usar *blueprints* si el proyecto ya los usa o `app.py` crece más allá de lo manejable; no reorganizar sin alcance.
- No introducir colas, caché, microservicios ni mensajería por defecto.

## 5. Diseño de contratos REST

### Recursos y semántica HTTP
- Nombres de recursos y URI consistentes con el proyecto (`/api/clientes`); conservar idioma y versionado existentes.
- GET seguro; PUT sustituye; PATCH modifica parcialmente; DELETE idempotente. POST no lo es.
- Creación: `201 Created` con `Location` si el contrato lo define. `204` sin cuerpo.
- Convención del proyecto (confirmar en `backend/app.py` antes de cambiarla): `422` datos de entrada inválidos, `409` conflicto (duplicado, estado), `403` permiso insuficiente, `404` inexistente o no visible, `401` sin autenticar, `400` solicitud malformada (p. ej. JSON ilegible). Cada código conserva siempre el mismo significado.
- Nunca responder `200` a un error ni exponer trazas, SQL o rutas internas.

### Entrada, validación y compatibilidad
- Validar en el borde: tipos, longitud, formato, rangos y campos permitidos (lista blanca). Evitar *mass assignment*: mapear campos explícitamente.
- Validaciones de formato en funciones reutilizables (teléfono de 10 dígitos, correo, CURP, RFC, placa, VIN, CP), con mensajes claros en español.
- Normalizar datos de forma consistente antes de guardar (espacios, mayúsculas/minúsculas) según las reglas del dominio.
- Importes con `Decimal`; fechas y zonas horarias con política explícita (UTC o local, documentada).
- No alterar contratos públicos silenciosamente; documentar cambios incompatibles.

### Colecciones
- Paginar listados con `page` y `page_size`; definir tamaño máximo y rechazar valores fuera de rango con error uniforme.
- Orden estable con desempate único (`ORDER BY ..., id ASC`); solo columnas de orden permitidas (lista blanca).
- Conservar el DTO de paginación existente (`page`, `page_size`, `total`, `pages`) salvo cambio autorizado.

### Errores uniformes
- Un único formato de error en toda la API (el existente: `error` + `errors` por campo).
- Centralizar con manejadores de error de Flask (`@app.errorhandler`); no repetir `try/except` en cada ruta.
- Mensajes públicos sin datos sensibles ni detalles internos; el detalle técnico va al log.

## 6. Seguridad desde el diseño

1. Definir activos, actores y amenazas del cambio antes de implementar.
2. **Denegar por defecto**: todo endpoint exige autenticación salvo los públicos declarados explícitamente.
3. Separar autenticación de autorización. Verificar **rol** y **objeto**: un token válido no da acceso a cualquier ID.
4. **Aislamiento por taller (multi-taller)**: toda consulta y escritura sobre datos de taller DEBE filtrar por el taller del usuario autenticado, salvo rol administrador con alcance explícito. Probar acceso cruzado entre talleres.
5. Consultas **siempre parametrizadas**; nunca construir SQL concatenando entrada del usuario. Los nombres de columnas u orden vienen de una lista blanca.
6. Contraseñas con hash adaptativo (`werkzeug.security` o `bcrypt`); nunca en texto plano ni con hashes rápidos.
7. Sesiones/tokens: expiración, cookies `Secure`/`HttpOnly`/`SameSite` si aplica. Si el navegador adjunta credenciales automáticamente, evaluar CSRF.
8. CORS con orígenes, métodos y encabezados mínimos; sin comodín con credenciales.
9. Secretos fuera de Git, logs y respuestas. Cuenta de MariaDB con privilegios mínimos.
10. Subida de archivos (fotos, máx. 15 MB): validar tamaño, tipo real (no solo extensión), nombre saneado y ruta fija; nunca ejecutar ni servir desde una ruta controlada por el usuario.
11. Registrar eventos de seguridad (login fallido, cambios de privilegio) sin credenciales ni datos personales innecesarios.
12. Rate limiting en login y endpoints costosos si están en alcance.

Pruebas mínimas cuando aplique: anónimo, token inválido o expirado, rol insuficiente, objeto ajeno, taller ajeno y entrada maliciosa.

## 7. Persistencia, transacciones y consultas (MariaDB)

### Integridad y modelo
- Definir PK, FK, `UNIQUE`, `NOT NULL` y `CHECK` según invariantes confirmadas. Una comprobación previa en Python no evita carreras: respaldar la unicidad en la BD y traducir el error de duplicado a `409`.
- **Nunca duplicar datos**: la regla de duplicados se aplica con índice único y se informa con mensaje claro.
- Migraciones **versionadas y numeradas** (`backend/migrations/NNN_descripcion.sql`); no modificar una migración ya aplicada, crear una nueva. Incluir cómo revertir cuando sea posible.
- Cambios incompatibles: enfoque *expand/contract* (añadir, migrar datos, retirar después). Sin migraciones destructivas sobre datos reales sin autorización.
- Eliminación **suave** (estatus/`deleted_at`) cuando el dominio lo exige; consultas filtran los registros eliminados por defecto.
- Catálogos con clave foránea (estatus, marcas, modelos) en lugar de cadenas libres.

### Transacciones y concurrencia
- Operaciones que modifican varias tablas (p. ej. alta de cliente + foto) DEBEN ir en **una sola transacción**: `commit` al final y `rollback` ante cualquier fallo.
- Si el proyecto registra auditoría, escribirla en la **misma transacción** que el cambio auditado.
- Cerrar siempre conexiones y cursores (`with` o `try/finally`); pool de conexiones solo si ya existe o se autoriza.
- Transacciones cortas; sin llamadas a servicios externos dentro de una transacción.
- Para conflictos de edición concurrente, evaluar una columna de versión o `updated_at` comparado; bloqueo pesimista solo con justificación.
- Reintentar deadlocks solo con límite y si repetir la operación es seguro.

### Consultas
| Necesidad | Alternativa | Evidencia necesaria |
|---|---|---|
| Consulta simple | SQL parametrizado en el repositorio | Resultado y parámetros |
| Filtros opcionales | Construir cláusulas desde lista blanca + parámetros | Predicados correctos, sin concatenar entrada |
| Lectura parcial | Seleccionar solo columnas necesarias | Columnas realmente consultadas |
| Relaciones | `JOIN` explícito | Sin N+1 (conteo de consultas) |
| Listados grandes | Paginación `LIMIT/OFFSET` o keyset | Orden estable, tiempo medido |

Protocolo para optimizar una consulta:
1. Especificar resultado, cardinalidad, filtros, permisos, orden y tamaño máximo.
2. Obtener SQL y parámetros representativos sin datos sensibles.
3. Medir con volumen relevante y revisar el plan con `EXPLAIN` (`EXPLAIN ANALYZE` ejecuta la consulta: solo en entorno seguro).
4. Revisar índices, escaneos completos, ordenamientos y joins.
5. Corregir el cuello de botella y comparar antes/después conservando resultados.
6. Añadir prueba de regresión y documentar límites.

Evitar: N+1, cargar todo para filtrar en Python, `SELECT *` innecesario, listados sin límite, índices en cada columna.

## 8. Rendimiento y operación

- No prometer rendimiento sin medición; definir carga, tamaño de datos, latencia objetivo y consumo si el requisito lo pide. Si faltan objetivos, registrarlos como pendientes.
- Timeouts en conexiones y consultas; límites de tamaño de petición (`MAX_CONTENT_LENGTH`, coherente con el máximo de 15 MB de fotos).
- Caché solo tras medir y definiendo consistencia, invalidación y aislamiento por taller.
- Logging con el módulo `logging`, con nivel y formato consistentes; sin tokens, contraseñas ni cuerpos completos. Incluir identificador de correlación si el proyecto lo usa.
- Endpoint de salud solo si está en alcance; no exponer configuración ni variables de entorno.
- Servidor de desarrollo de Flask solo para desarrollo; producción con servidor WSGI (gunicorn/waitress) si el despliegue está en alcance.

## 9. Código y documentación mantenibles

- PEP 8, nombres del dominio, funciones pequeñas con una responsabilidad.
- *Type hints* en funciones nuevas o modificadas; evitar `Any` innecesario.
- Excepciones específicas; nunca `except:` o `except Exception:` para silenciar fallos.
- Sin código duplicado; reutilizar validadores y utilidades existentes.
- Docstrings en contratos públicos relevantes (invariantes, errores, efectos); comentarios para explicar decisiones, no cada línea.
- La documentación de fase y sprint (`docs/backend/`) la genera la etapa Documentación del orquestador; no editarla a mano durante la implementación. Ejemplos siempre ficticios, nunca datos reales.
- README operativo con versiones, arranque, `.env.example`, migraciones y pruebas, solo si cambia.

## 10. Estrategia de validación

| Nivel | Qué verificar | Herramienta |
|---|---|---|
| Unitario | Validadores, reglas de negocio, normalización | pytest |
| Ruta / contrato | Códigos HTTP, validación, errores uniformes | pytest + `app.test_client()` |
| Seguridad | Autenticación, rol, objeto y taller ajeno | pytest |
| Persistencia | Constraints, duplicados, transacción y rollback | pytest contra MariaDB de pruebas |
| Migraciones | Aplican desde cero y sobre datos existentes | Ejecución real en BD de pruebas |
| Rendimiento | Objetivos bajo carga representativa | Herramienta ya existente o autorizada |

- No sustituir MariaDB por SQLite para validar SQL específico de MariaDB.
- Evitar mocks que solo reproduzcan la implementación; probar comportamiento.
- Cada corrección incluye su prueba de regresión.
- Ejecutar los comandos reales del repositorio y guardar comando, resultado y limitación. Una prueba no ejecutada se reporta como pendiente, nunca como aprobada.

## 11. Definition of Done

- [ ] Todos los requisitos incluidos tienen criterio de aceptación y evidencia.
- [ ] El diff contiene solo cambios solicitados o indispensables y justificados.
- [ ] Pruebas aplicables ejecutadas y pasando; bloqueos declarados.
- [ ] Contrato, errores, autorización y aislamiento por taller validados en los flujos afectados.
- [ ] Consultas y migraciones verificadas contra MariaDB si cambiaron.
- [ ] Documentación afectada actualizada; sin secretos en el código ni en Git.
- [ ] Rendimiento reclamado respaldado por medición reproducible.
- [ ] Tabla de fases y resumen ejecutivo conforme a `orquestador-backend.md`.

## 12. Versionado y changelog

- Por cada iteración se mejora el archivo y se incrementa `version` (patch / minor / major, igual que en `orquestador-backend.md`).
- Toda modificación se registra aquí.

| Versión | Cambios |
|---------|---------|
| 1.1.0   | Motor real MariaDB 11 con PyMySQL; convención de códigos 422/409/403/404 del proyecto; auditoría en la misma transacción; documentación delegada a la etapa Documentación. |
| 1.0.0   | Versión inicial para Python + Flask + MariaDB: SPEC, contratos REST, seguridad con aislamiento por taller, persistencia, validación con pytest y Definition of Done. |
