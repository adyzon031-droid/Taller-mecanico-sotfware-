# Estándar de documentación — Torque · Taller mecánico

Estándar compartido por `documents-backend.md` y `documents-frontend.md`. Sistema: Vue estático → Facade → Repository → API Flask → MariaDB 11, multi-taller. Se documenta por proyecto, sprint y fase, con un diagrama Mermaid y un modelo importable en Archi (CSV). Español, tono técnico y directo.

## 1. Reglas

- Documenta **solo lo que veas** en el código, los archivos o el texto entregado. No inventes rutas, columnas, funciones, componentes ni relaciones.
- Si falta código para documentar algo, pídelo o escribe "No encontrado". Nunca lo supongas.
- No pidas ni repitas `.env`, contraseñas, tokens ni datos personales. Ejemplos siempre ficticios.
- No modifiques código: solo escribes en `docs/`.
- "Verificado" solo si el usuario entrega el resultado real de una prueba ejecutada; si no, "No verificado".
- Ante una ambigüedad, asume lo más coherente con el código y decláralo en una línea al final.

## 2. Datos de entrada

Antes de documentar, confirma que tienes: fase (número y slug), sprint (opcional), archivos creados o modificados, UC afectados y resultados reales de pruebas (totales antes y después). Si falta algo esencial, pídelo en **una sola pregunta**.

Backend: pruebas con `pytest`. Frontend: no hay runner; la verificación es manual y solo se marca "Verificado" con el resultado real aportado.

## 3. Archivos de salida

Ruta base: `docs/<backend|frontend>/`

- `proyecto.md`
- `sprints/sprint-NN.md`
- `fases/fase-NN-<slug>/fase.md`
- `fases/fase-NN-<slug>/diagrama.mmd`
- `fases/fase-NN-<slug>/archi/elementos.csv`
- `fases/fase-NN-<slug>/archi/relaciones.csv`
- `fases/fase-NN-<slug>/archi/propiedades.csv`

El slug va en minúsculas con guiones (`fase-01-gestion-clientes-vehiculos`). Si el cambio toca ambas capas, cada una se documenta en su carpeta como entrega separada (primero backend, luego frontend).

## 4. Contenido

### fase.md
1. Alcance y UC: tabla `UC | Nombre | Estado | Evidencia | Observaciones`. Estados: Hecho, Realizado ahora, Pendiente, No leído.
2. Resumen de la capa en esa fase.
3. Elementos documentados. Backend: tablas y endpoints. Frontend: vistas, componentes, facades y repositories. Cada función con nombre, ubicación, capa, propósito, parámetros y retorno.
4. Diagrama (el contenido de `diagrama.mmd` en un bloque `mermaid`).
5. Pruebas: comando, total antes/después y resultado real.
6. Pendientes, supuestos y decisiones.

### proyecto.md
- **Backend:** stack y carpetas; variables de entorno (solo nombres); esquema (tabla, columnas, tipos, FK, índices, triggers, migración); endpoints (`Método | Ruta | Permisos | Parámetros | Respuestas | Verificado`); funciones; seguridad y multi-taller; auditoría y errores (422, 409, 403, 404); pruebas.
- **Frontend:** stack y carpetas; flujo Vista → Store → Facade → Repository → API cuando aplique; vistas y componentes (props, eventos, facade que usan); stores aprobados (forma de estado, sin datos personales ni secretos), facades y repositories (función, parámetros, retorno, endpoint); estado local en `data`; validaciones; pruebas (verificación manual).

### sprint-NN.md
Objetivo único y medible; alcance (`ID | Nombre | Estado | Evidencia | Qué falta`); definición de terminado con casillas; cambios por capa; pruebas antes/después; pendientes y riesgos; retrospectiva (qué funcionó, qué mejorar, acción con responsable y fecha).

## 5. Diagrama (`diagrama.mmd`)

Mermaid `flowchart LR`, o `erDiagram` para el esquema del backend. Solo elementos que existen en el código de esa fase. Si una vista salta una capa, dibújalo tal cual y repórtalo en Observaciones.

## 6. Modelo Archi (CSV UTF-8, todos los campos entre comillas, con encabezados)

Se importa en Archi con *File → Import → CSV Data Into Selected Model* (con un modelo vacío seleccionado).

- `elementos.csv`: `"ID","Type","Name","Documentation"`
- `relaciones.csv`: `"ID","Type","Name","Documentation","Source","Target"`
- `propiedades.csv`: `"ID","Key","Value"`

IDs únicos y estables (ej. `f01-vista-clientes`). `Source`, `Target` y los ID de propiedades deben existir en los CSV.

- Tipos de elemento: ApplicationComponent, ApplicationInterface, ApplicationService, ApplicationFunction, DataObject, Node, SystemSoftware, BusinessProcess, BusinessActor.
- Tipos de relación: ServingRelationship, CompositionRelationship, FlowRelationship, TriggeringRelationship, AccessRelationship, RealizationRelationship, AssignmentRelationship, AssociationRelationship.
- Propiedades útiles: capa, archivo, fase, verificado.

El diagrama Mermaid y los CSV deben contener los mismos elementos y relaciones.

## 7. Prácticas que debes reflejar o señalar

- **Frontend:** flujo Vista → Store → Facade → Repository → API cuando aplique; `fetch` solo en repositories; validaciones en una utilidad compartida; componentes en PascalCase de varias palabras; Options API. Señala como observación cualquier vista que llame a la API directamente. TypeScript y Composition API no se usan hoy; Pinia solo aparece para estado compartido autorizado: si se sale de esa regla, repórtalo.
- **Backend:** capas ruta → fachada → repositorio; el backend es la autoridad de validación; códigos 422, 409, 403 y 404 con significado fijo; migraciones numeradas e idempotentes; auditoría en la misma transacción.
- **Sprint:** un objetivo medible, definición de terminado explícita, evidencia por entrega, métricas reales de pruebas.

## 8. Revisión antes de entregar

- Cada elemento documentado existe en el código entregado y con el nombre exacto.
- Sin datos sensibles ni valores de `.env`.
- Los CSV tienen el mismo número de columnas en cada fila; diagrama y CSV coinciden.
- Lo no probado dice "No verificado".

## 9. Respuesta final

Solo: archivos escritos, secciones actualizadas y la lista de pendientes ("No verificado", "No encontrado", "No leído").
