# Revisión del flujo del Módulo B (HU-B01 … HU-B14) — 2026-07-25

Revisión completa del Módulo B (Catálogo, Inventario, Ingresos, Mermas y Proveedores):
dominio, casos de uso, adaptadores, routers, esquema de BD, seed y contrato con el
frontend. Se detectaron **25 problemas** y **los 25 quedaron corregidos y verificados
contra la base de pruebas de Supabase**.

| | |
|---|---|
| Endpoints revisados | 33 rutas en 7 routers (productos, categorías, ingresos, mermas, proveedores, movimientos, storage) |
| Problemas encontrados | 25 (5 bloqueantes, 10 altos, 8 medios, 2 detectados durante la corrección) |
| Problemas corregidos | 25 |
| Suite del Módulo B | **100 passed** (unit + e2e contra Supabase, 8 m 23 s) |
| Verificación en vivo HU-B01…B14 | **43 comprobaciones, 0 fallas** |
| `xfail` eliminados | 4 (eran bugs de producción; ahora pasan de verdad) |
| Tests nuevos de regresión | 13 |

---

## 1. Cómo se verificó

1. **Lectura completa del módulo**: 30 casos de uso, 9 adaptadores SQLAlchemy + storage, 7 routers,
   entidades, VOs, puertos, `module_container`, `schemas.py`, seed y DDL.
2. **Banco de pruebas en proceso** (primera pasada): la app FastAPI real por ASGI,
   replicando el `CHECK chk_mermas_estado_consistente` que solo vive en
   `db/schema_modulo_b_completo.sql`. Sirvió para reproducir los 500 sin tocar la BD
   compartida.
3. **Verificación final contra Supabase** (`DATABASE_URL` de `backend/.env`): recorrido
   HU-B01 → HU-B14 con usuarios ADMIN y CAJERO reales, 43 aserciones. Los datos creados
   por la corrida quedan dados de baja lógica (las tablas `historial_precios` y
   `movimientos_inventario` son append-only por trigger).
4. **Suite oficial del módulo** (`pytest tests/modulo_b_inventario`) contra la misma BD.

---

## 2. Problemas encontrados y cómo se corrigieron

### 🔴 Bloqueantes

#### B1. `PATCH /mermas/{id}` respondía 500 siempre
* **Síntoma**: cualquier edición de merma devolvía 500.
* **Causa**: `mermas_router.py` pasaba `foto_url=...` y `EditarMermaUseCase.ejecutar()`
  no declara ese parámetro → `TypeError`. Los tests unitarios llaman al caso de uso
  directamente, por eso nunca se detectó.
* **Corrección**: se eliminó el argumento del router (`mermas_router.py:172`).
* **Verificado**: `PATCH /mermas/{id}` con `{"cantidad": 2}` → 200 y la merma queda en 2.

#### B2. `POST /mermas/{id}/confirmar` rompía contra Postgres
* **Síntoma**: 500 al confirmar; la merma **nunca descontaba stock** (HU-B12 sin cumplir).
* **Causa**: `Merma.confirmar()` no seteaba `confirmado_en`, y el CHECK

  `chk_mermas_estado_consistente` exige ese timestamp cuando `estado='Confirmada'`.
  Era el gemelo exacto del bug que ya se había arreglado en `rechazar()`.
* **Corrección**: `entities.py:390` setea `confirmado_en = now(utc)` en la transición.
* **Verificado**: confirmar → 200, `stock_actualizado`, y stock 30 → 28 en BD.

#### B3. Cinco permisos usados por los routers no existían en el seed
* **Síntoma**: 403 para todos —incluida la administradora— en mermas, historial de
  precios, subida de boletas y alta de categorías. `require_permission` consulta la BD y
  **no tiene bypass de ADMIN**.
* **Causa**: `scripts/seed.py` no creaba `mermas.registrar`, `mermas.confirmar`,
  `categorias.gestionar`, `historial_precios.ver` ni `storage.upload` (solo estaban en el
  DDL de `db/`, aplicado a mano). Y al revés: `proveedores.ver` estaba en el seed pero no
  en el DDL, así que **en la BD de pruebas `GET /proveedores` daba 403 para todos**.
* **Corrección**: los 5 permisos se agregaron a `scripts/seed.py` (con `mermas.registrar`
  y `storage.upload` también para CAJERO, que es quien registra la merma y adjunta la
  boleta) y `proveedores.ver` se agregó a `db/schema_modulo_b_completo.sql` con su
  asignación a ADMIN y CAJERO. Ambas fuentes quedaron alineadas y son idempotentes.
* **Verificado**: aplicado a Supabase; CAJERO lista y abre proveedores, registra mermas y
  sube archivos.

#### B4. `POST/PATCH /categorias` y `PATCH /proveedores` respondían 500
* **Síntoma**: crear categoría con descripción, editar categoría y editar proveedor →
  500 `sqlalchemy.exc.MissingGreenlet`.
* **Causa**: los repos leían `updated_at` sobre el modelo **recién flusheado**. Como esa
  columna tiene `onupdate=func.now()`, SQLAlchemy la deja expirada y el acceso dispara un
  SELECT de refresco fuera del greenlet async.
* **Corrección**: `await self._db.refresh(fila)` antes de mapear a entidad en
  `sqlalchemy_categoria_repository.py` y `sqlalchemy_proveedor_repository.py`. Además
  ambos `scalar_one()` pasaron a `scalar_one_or_none()` + `NoEncontradoError`, así un id
  inexistente devuelve **404 en vez de 500**.
* **Verificado**: los 3 endpoints en 200/404 y los 2 `xfail` que documentaban el bug ahora
  pasan sin marca.

#### B5. El esquema del módulo no estaba en las migraciones y había dos *heads*
* **Síntoma**: en un entorno nuevo `alembic upgrade head` abortaba con *"Multiple head
  revisions are present"*, y aunque se forzara, la 0013 fallaba porque hacía `ADD COLUMN`
  sobre `solicitudes_ingreso`, que **ninguna migración creaba**. Las 7 tablas del módulo
  solo existían en `db/schema_modulo_b_completo.sql`, aplicado a mano.
* **Corrección**:
  * `0012a_modulo_b_esquema_completo.py` (nueva): crea el esquema ejecutando el DDL
    canónico de `db/` (idempotente), recortando la sección que aplica la 0013.
  * `0013_...` ahora cuelga de `0012a` en vez de `0012`.
  * `0014_merge_heads_b_c_d.py` (nueva): une las dos cabezas (Módulo B y el merge C/D).
  * `0015_modulo_b_alerta_stock.py` (nueva): columna de alerta de HU-B13.
* **Verificado**: `alembic heads` → **una sola cabeza** (`0015_modulo_b_alerta_stock`).

---

### 🟠 Altos

#### A1. La validación anti-colisión de códigos era código muerto (HU-B03)
`crear_producto_usecase.py` levantaba el `ValidacionError` **dentro** del `try` cuyo
`except ValidacionError: pass` se lo tragaba: un código de barras `PAP-001` se aceptaba.
Se extrajo el chequeo a `_tiene_formato_de_codigo_interno(codigo, prefijo)`, que solo
bloquea los que usan el prefijo real del sistema (`PAP-NNN`) — un código manual tipo
`BC-12345` sigue siendo válido. **Verificado**: `PAP-001` → 422, `BC-34567` → 201.

#### A2. El "código interno" no era un correlativo (HU-B03)
Generaba `PAP-{HHMMSS}` y ante colisión concatenaba `"X"` (`PAP-223902X`), que ni es
correlativo ni cumple el patrón del VO; dos altas en el mismo segundo se pisaban.
Ahora `ProductoRepositoryPort.siguiente_correlativo_interno()` calcula el máximo real y
devuelve `PAP-001`, `PAP-002`, … serializado con un **advisory lock de Postgres** por
prefijo, que elimina la carrera. **Verificado**: `PAP-002` en la BD real y
`["PAP-001","PAP-002","PAP-003"]` en test unitario.

#### A3. Los PATCH de ingresos y mermas no validaban las FKs
`proveedor_id`/`producto_id` inexistentes llegaban al UPDATE y Postgres respondía con
violación de FK (500), pese a que el propio docstring prometía 422. Se inyectaron los
repos de producto y proveedor en `EditarIngresoUseCase` y `EditarMermaUseCase` y se
validan antes de mutar, con códigos `PRODUCTO_NOT_FOUND` / `PROVEEDOR_NOT_FOUND`.

#### A4. `PATCH /productos` ignoraba `precio` en silencio (HU-B11)
La "defensa" del router nunca disparaba porque Pydantic descartaba el campo no declarado:
el endpoint respondía 200 y el precio no cambiaba. `ProductoUpdate` ahora es
`extra="forbid"` → **422**. Mismo criterio en `ProveedorUpdate`, `PagoProveedorCreate`,
`CambiarPrecioRequest` y `AprobarIngresoRequest`.

#### A5. Se podía dejar un producto con precio de venta 0
`CambiarPrecioRequest.precio_venta` era `ge=0` mientras el alta exige `> 0`. Ahora es
`gt=0` en el schema y `<= 0 → ValidacionError` en `CambiarPrecioUseCase`.

#### A6. HU-B13 no tenía "alerta única" y el listado hacía ruido
No existía ningún estado de alerta y, como el filtro era `stock <= stock_minimo`,
**todo producto con `stock_minimo = 0` y sin stock aparecía como "por reponer"**.
* `productos.alerta_stock_notificada` (migración 0015 + DDL): se marca al avisar y
  **se rearma sola** cuando el stock vuelve a superar el mínimo (tanto al aprobar un
  ingreso como al reponer por devolución).
* `GET /productos/por-reponer?solo_no_notificadas=true` y
  `POST /productos/por-reponer/marcar-notificadas` (nuevo).
* `stock_minimo > 0` como condición, en el repo y en `Producto.requiere_reposicion()`.

#### A7. El precio de compra de la boleta no llegaba al producto (HU-B05/B11)
Se guardaba en el detalle de la solicitud y ahí moría. Al aprobar, `AprobarIngresoUseCase`
ahora actualiza `precio_compra_actual` por cada línea reutilizando `actualizar_precio()`,
que deja la fila correspondiente en `historial_precios`.
**Verificado**: ingreso a 1900 → producto con `precio_compra_actual = 1900` e historial.

#### A8. La deuda del proveedor no se generaba al aprobar el ingreso (HU-B14)
Había que cargarla a mano y sin vínculo; peor: `POST /proveedores/{id}/pagos` aceptaba
`solicitud_ingreso_id` y **lo descartaba en silencio** (el CHECK de la tabla lo prohíbe).
* `POST /ingresos/{id}/aprobar` acepta `{"registrar_credito": true}` y carga la compra a
  crédito por el monto total, vinculada a la solicitud, **en la misma transacción**.
* La respuesta suma `monto_total` y `credito_registrado`.
* `/pagos` con `solicitud_ingreso_id` → **422** explícito.
**Verificado**: aprobación de 20 × 1900 → deuda del proveedor 38 000.

#### A9. La foto de la boleta caducaba a las 24 h (HU-B07/B08)
La URL firmada se guardaba permanentemente en `foto_boleta_url`, así que al día siguiente
la administradora ya no podía ver la boleta. El TTL pasó a ser configurable
(`SUPABASE_SIGNED_URL_TTL`, 1 año por defecto) y se agregó `POST /storage/firmar` para
regenerar la URL desde el `path`. Además `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y los
buckets **no estaban documentados en `.env.example`** (sin ellos no se puede adjuntar la
boleta y HU-B06 queda bloqueada): ya están.

#### A10. `PATCH /proveedores` podía borrar los datos del proveedor
Si `find_by_id` devolvía `None` (id inexistente o borrado lógico), el caso de uso
construía la entidad con `""`/`None` y el UPDATE **pisaba la razón social y el RUC**
(reproducido: `razon_social` quedó en `''`). Quedaba enmascarado por el 500 de B4, que
hacía rollback. Ahora falta el proveedor → `NoEncontradoError` (404) y los campos no
enviados conservan su valor anterior.

---

### 🟡 Medios

| # | Problema | Corrección |
|---|---|---|
| M1 | Cualquiera con `inventario.ver` veía mermas ajenas y quien registraba podía confirmar su propia merma (D-14 pide 2 pasos) | El CAJERO solo ve/lista las suyas (simetría con `/ingresos`) y no puede confirmar la propia (`SELF_CONFIRM_FORBIDDEN`); la ADMIN sí, porque HU-B12 dice que ella registra y valida |
| M2 | Las ventas y devoluciones **no dejaban asiento** en `movimientos_inventario` (D-07: bitácora de *toda* variación de stock) | `SqlAlchemyStockAdapter` inserta `tipo='venta'` / `'devolucion'` en la misma transacción; el puerto lleva ahora el usuario que la origina |
| M3 | `GET /ingresos` como CAJERO ignoraba `proveedor_id` y las fechas (respondía 200 sin filtrar) | `listar_por_solicitante()` recibe y aplica los mismos filtros que el listado general |
| M4 | `PATCH /productos` con `categoria_id: null` no desasignaba (los `None` se descartaban) | `categoria_id` y `foto_url` aceptan NULL explícito; el resto sigue ignorando `None` |
| M5 | El PATCH de proveedor no validaba el email (el alta sí) y se podían registrar compras a crédito a proveedores dados de baja | Validador compartido `_normalizar_email` y bloqueo de compras a crédito si el proveedor está inactivo (los **pagos sí** se permiten, para saldar deuda) |
| M6 | Reusar el código de un producto borrado lógicamente → 500 (el UNIQUE es global) | `existe_codigo()` mira también los borrados → 409 con mensaje claro |
| M7 | `GET /proveedores/{id}` exigía `proveedores.gestionar` mientras el listado pedía `proveedores.ver`: el cajero listaba pero no podía abrir el detalle | El detalle usa `proveedores.ver` |
| M8 | `POST /categorias` no persistía `descripcion` ni `creado_por`: insertaba solo el nombre y hacía un UPDATE extra (el que reventaba en B4) | El puerto `crear()` recibe la entidad completa y persiste todo en un solo INSERT |

---

### 🆕 Detectados durante la corrección (con la verificación en vivo)

#### N1. El PATCH parcial borraba los campos que no mandabas
`PATCH /mermas {"cantidad": 2}` respondía **422 INVALID_MOTIVO**, y
`PATCH /ingresos {"lineas": [...]}` **borraba el proveedor** de la solicitud: los routers
mandaban `None` para los campos ausentes y el dominio lo interpretaba como "poné este
campo en null" en vez de "no lo toques". Ahora los schemas exponen `valor(campo)`, que
devuelve el sentinel `...` cuando el campo no vino en el body (`model_fields_set`), y la
validación de "al menos un campo" también usa `model_fields_set` — así mandar
`{"observacion": null}` sigue siendo una forma válida de limpiar el valor.

#### N2. Los 422 de validadores propios salían como 500
Cuando un validador levanta `ValueError`, Pydantic guarda la excepción en `ctx["error"]`;
ese objeto no es serializable y `JSONResponse` fallaba **dentro** del handler, así que el
422 terminaba como 500 (se vio con el email inválido del proveedor). El handler de
`RequestValidationError` ahora normaliza `ctx` a texto antes de responder.

---

## 3. Lo que ya estaba bien

* **HU-B10 correcto**: descuento atómico condicional en la misma transacción de la venta
  (`UPDATE ... WHERE stock >= :cantidad`), CHECK `stock >= 0` en BD y 409 si no alcanza.
  El stock nunca queda negativo. Lo único que faltaba era la bitácora (M2).
* Flujo de 2 pasos de ingresos (pendiente sin tocar stock, foto obligatoria, aprobación
  transaccional, rechazo con motivo, 409 en doble revisión) y aislamiento del CAJERO.
* Historial de precios append-only con trigger, sin filas duplicadas si el precio no cambia.
* Deuda de proveedores: RUC único, pago ≤ deuda, deuda no negativa.

---

## 4. Cambios que impactan al frontend

| Endpoint | Cambio |
|---|---|
| `PATCH /productos/{id}` | Mandar `precio` o `precio_compra_actual` ahora es **422** (antes 200 silencioso) |
| `PATCH /productos/{id}/precio` | `precio_venta` debe ser **> 0** |
| `POST /ingresos/{id}/aprobar` | Body opcional `{"registrar_credito": bool}`; respuesta suma `monto_total` y `credito_registrado` |
| `POST /proveedores/{id}/pagos` | `solicitud_ingreso_id` ahora es **422** (va en `/compras-credito`) |
| `GET /productos/por-reponer` | Nuevo filtro `solo_no_notificadas`; cada ítem trae `alerta_notificada` |
| `POST /productos/por-reponer/marcar-notificadas` | **Nuevo** — `{"producto_ids": [...]}` |
| `POST /storage/firmar` | **Nuevo** — regenera la URL de una boleta a partir de su `path` |
| `GET /proveedores/{id}` | Ahora pide `proveedores.ver` (antes `proveedores.gestionar`) |
| `GET /mermas`, `GET /mermas/{id}` | El CAJERO solo ve las suyas; confirmar la propia da 403 |

---

## 5. Archivos tocados

**Dominio y aplicación (Módulo B)**: `domain/entities.py`, 4 puertos
(`producto`, `categoria`, `merma`, `solicitud_ingreso`, `storage`), y los casos de uso
`crear_producto`, `crear_categoria`, `editar_proveedor`, `aprobar_ingreso`,
`confirmar_merma`, `editar_ingreso`, `editar_merma`, `listar_ingresos`, `listar_mermas`,
`listar_productos_por_reponer`, `cambiar_precio`, `registrar_compra_credito`.

**Infraestructura (Módulo B)**: `models.py`, repos de producto/categoría/proveedor/merma/
solicitud, `supabase_storage_adapter.py`, routers de productos/categorías/ingresos/mermas/
proveedores/storage, `schemas.py`, `module_container.py`.

**Transversal y Módulo C**: `app/shared/http/error_handlers.py`,
`modulo_c_ventas/domain/ports/producto_stock_port.py`,
`sqlalchemy_stock_adapter.py`, `registrar_venta_usecase.py`, `anular_venta_usecase.py`.

**Datos e infraestructura**: `scripts/seed.py`, `db/schema_modulo_b_completo.sql`,
4 migraciones (`0012a`, `0013` reencadenada, `0014` merge, `0015`), `.env.example`.

**Tests**: `_mocks.py`, `test_unit_correcciones.py` (nuevo, 13 tests),
`test_unit_cambiar_precio_full.py`, y los 3 e2e de los que se quitaron los `xfail`.

---

## 6. Pendientes / recomendaciones

1. **Correr `python -m scripts.seed`** en cada entorno para que aparezcan los 5 permisos
   nuevos (en la BD de pruebas ya se aplicaron vía `scripts.aplicar_schema`).
2. La BD de pruebas tiene `alembic_version = '0013_modulo_d_respaldo_drive'`, una revisión
   que **no existe en esta rama**: alembic no puede correr ahí hasta que se decida si esa
   BD se re-estampa (`alembic stamp 0015_modulo_b_alerta_stock`) o se rehace. Las
   migraciones nuevas ya dejan una cadena consistente para entornos limpios.
3. Un test de humo que recorra las 33 rutas y solo verifique "no 500" habría cazado B1, B2
   y B4; los unitarios con mocks no ven ni los CHECK de la BD ni las firmas de los routers.
4. Un test que compare los `require_permission("...")` del código contra la lista del seed
   evitaría para siempre la clase de bug B3.
5. Guardar el `path` de la boleta además de la URL permitiría refirmar sin depender de que
   el frontend recuerde el path (hoy `POST /storage/firmar` lo recibe por parámetro).

---

## 7. Anexo — el frontend ya no depende del tamaño del catálogo (2026-07-25, 2ª pasada)

Revisando el log de uvicorn aparecieron dos problemas más, ambos del frontend:

### F1. Bucle infinito de requests
`useProductos({ page_size: 200 })` crea un objeto **nuevo en cada render** y los hooks
lo usaban como dependencia del `useEffect` que hace `setState`: efecto → fetch →
setState → render → objeto nuevo → efecto… El log mostraba `/productos` y
`/proveedores` repitiéndose sin parar desde 6 conexiones.
Afectaba a `useProductos`, `useProveedores`, `useMermas`, `useIngresos` y `useMovimientos`.

**Corrección**: `shared/lib/use-filtros-estables.ts` devuelve una clave estable por
contenido (`JSON.stringify`) más una ref con el último valor; los efectos dependen de
la clave, no de la identidad del objeto.

### F2. `page_size=200` → 422 y selectores vacíos
El backend limita `page_size` a 1-100, así que esas 5 pantallas recibían 422, el error
se descartaba en silencio y los selectores quedaban vacíos. Subir el tope solo movía el
problema: la causa real era que el front cargaba **todo el catálogo** para dos cosas.

**Corrección de fondo** (independiente del volumen de datos):

1. **El nombre del producto viaja en la respuesta** (JOIN en el repo, sin migración),
   igual que ya se hace con `solicitado_por_nombre` y compañía:

   | Respuesta | Campos nuevos |
   |---|---|
   | `DetalleResponse` (líneas de ingreso) | `producto_nombre`, `producto_codigo` |
   | `MermaResponse` | `producto_nombre`, `producto_codigo` |
   | `MovimientoInventarioResponse` | `producto_nombre`, `producto_codigo` |

   Se eliminó el `nombreProducto(id)` de las 4 páginas y los 2 componentes de detalle.

2. **Los filtros y el alta de líneas usan búsqueda server-side**: `SelectorProducto`
   (debounce 300 ms contra `/productos/buscar`) reemplaza a los `<select>` que
   volcaban el catálogo completo en `Mermas`, `MovimientosInventario` y
   `FormularioLineaIngreso`.

Resultado: **ninguna pantalla carga el catálogo entero**, el tope de `page_size` deja de
importar y el front no vuelve a romperse en silencio cuando el catálogo crezca.
Verificado contra Supabase: 9/9 comprobaciones de los campos nuevos y `tsc --noEmit` limpio.

### F3. `NameError` al arrancar el servidor
`lifespan()` llamaba a `_ejecutar_tarea_reintentar()`, cuya definición se había perdido
en la resolución de conflictos de `1f2f8ec` (en `53f51f5` sí estaba). Se quitó la
llamada: la tarea, tal como está escrita, re-sube todas las ventas de los últimos 7 días
cada 5 minutos sin registrar lo ya subido. El módulo `reintentar_subidas.py` queda en el
repo por si Módulo D quiere arreglar la idempotencia y volver a engancharlo.

---

## 8. Anexo — reestructuración de vistas y baja de mermas (2026-07-25, 3ª pasada)

Cambio de alcance pedido por el equipo. **El flujo de mermas se eliminó** y las
tres vistas del frontend se reorganizaron en dos.

### Mermas fuera
Se borraron los 5 casos de uso, el puerto, el repositorio, el router (6 endpoints),
la entidad `Merma`, sus VOs (`EstadoMerma`, `MotivoMerma`), los schemas, las 2
páginas, 3 componentes, hook y servicios del frontend, y los permisos
`mermas.registrar` / `mermas.confirmar` del seed.

**La tabla `mermas` se conserva en la BD** (documentada como histórica en
`models.py`): `movimientos_inventario.merma_id` la referencia con FK y las mermas
ya registradas son parte del histórico contable.

Su reemplazo es el **ajuste manual de stock** desde el catálogo:
`POST /productos/{id}/ajustar-stock` con `delta` (+/-) y `motivo` obligatorio,
permiso nuevo `inventario.ajustar_stock` (solo ADMIN). Cada ajuste deja su asiento
en `movimientos_inventario` (`tipo='ajuste'`) y en la bitácora. El stock nunca
queda negativo: el UPDATE es atómico y devuelve 409 si no alcanza.

También se agregó `DELETE /productos/{id}` (baja lógica; el histórico se conserva,
las FKs del módulo son `ON DELETE RESTRICT`).

### Las vistas
| Antes | Ahora |
|---|---|
| Catálogo (solo lectura, cartillas en el POS) | **eliminada**: `/catalogo` ahora es la de gestión; `/productos` redirige ahí |
| Punto de venta (productos como cartillas) | **tabla de consulta**: código, nombre, categoría, precio, stock y estado, con filtros |
| Productos+ (gestión, solo ADMIN) | **renombrada a Catálogo**, con edición en planilla |

**Punto de venta**: la tabla es la vista de solo lectura del catálogo. Se carga un
producto a la venta de dos formas: haciendo clic/tap en su fila, o escaneándolo
(estando en la pestaña, el lector escribe en el buscador y al Enter se agrega). Si
el código escaneado no está en la página cargada, se lo pide al backend por
`GET /productos/buscar?codigo=`, así el escaneo no depende de los filtros ni de la
paginación. Filtros: texto (nombre/código), categoría, estado de stock y rango de
precio — los tres últimos requirieron `sin_stock`, `precio_min` y `precio_max` en
`GET /productos`.

**Catálogo (ADMIN)**: edición tipo planilla. El lápiz de la fila la vuelve editable
en el lugar (código, nombre, categoría, precio, stock y stock mínimo); el lápiz pasa
a ser un diskette y, al guardarlo, la fila muestra *"¿Seguro que querés hacer este
cambio?"* con ✓ / ✗. Recién con el ✓ se aplican los cambios, cada uno por su
endpoint: `PATCH /productos/{id}` (datos), `PATCH /precio` (precio) y
`ajustar-stock` (diferencia de stock, con motivo automático).

### Verificación
- Suite del Módulo B: **84 passed** (se fueron los 16 tests de mermas).
- Contra Supabase: **26 comprobaciones, 0 fallas** (mermas 404 en las 5 rutas,
  ajuste +/- con sus asientos, tope de stock, permisos ADMIN vs CAJERO, filtros
  nuevos, escaneo por código y baja lógica con historial conservado).
- `tsc --noEmit` limpio.

---

## 9. Anexo — sin fotos, escáner en ingresos y alta en planilla (4ª pasada)

### 9.1 Los productos ya no llevan foto
Se eliminó `foto_url` de la entidad, el modelo, los schemas, el caso de uso, el
repositorio, los tipos del frontend y la vista de catálogo. `ProductoCreate` pasó
a `extra="forbid"`, así que mandarlo ahora devuelve **422** en vez de descartarse
en silencio. La carpeta `productos` salió de `CARPETAS_VALIDAS` del storage: el
único destino válido es `boletas` (la foto de la boleta de ingreso SÍ sigue siendo
obligatoria, HU-B06).

La columna `productos.foto_url` se conserva en la BD pero ya **no se mapea** en
`models.py` (documentado ahí mismo).

### 9.2 Ingresos: misma regla de escaneo que el POS
En la pestaña de ingresos, escanear un código —o escribir el nombre y dar Enter—
busca el producto y lo agrega como línea:
- si ya está en la solicitud, suma 1 a su cantidad;
- si hay una línea vacía, la ocupa;
- el precio de compra se pre-carga con el `precio_compra_actual` del producto.

El foco vuelve solo al buscador si se perdió (el lector "tipea" donde esté el
cursor). Cuando el código no existe, el aviso lo dice y **se desvanece a los 4
segundos** (`lib/useAvisoTemporal.ts`), para no tapar el siguiente escaneo. Si el
texto coincide con varios productos por nombre, avisa cuántos son en vez de
elegir uno al azar.

### 9.3 Catálogo: el alta también es una fila
"Nuevo producto" ya no abre un modal: inserta una **fila vacía editable arriba de
la tabla**, con las mismas columnas y el mismo ciclo que la edición
(diskette → "¿Creamos este producto?" → ✓ / ✗). Enter guarda y Escape descarta,
para poder cargar sin soltar el teclado.

### Verificación
- Suite del Módulo B: **84 passed**.
- Contra Supabase: **13 comprobaciones, 0 fallas** (alta completa en una llamada,
  `foto_url` rechazado en alta y PATCH, edición de fila por sus tres endpoints,
  escaneo por código y por nombre, 404 del código inexistente, y `carpeta=productos`
  rechazada en storage).
- `tsc --noEmit` limpio.

---

## 10. Anexo — paginación de Notas de Venta (5ª pasada)

`GET /notas-venta` devolvía **todas** las notas del rango en una sola respuesta y
la página las acumulaba en memoria, cortándolas de a 20 en el cliente: con el
tiempo la tabla se hacía interminable y cada consulta traía el histórico completo.

- **Backend**: el endpoint acepta `page` / `page_size` (1-100, igual que el resto)
  y devuelve el envoltorio estándar `{items, total, page, page_size, total_pages}`.
- **Frontend**: `PaginacionControles` —que ya usaban las tablas de inventario y
  el POS— se movió a `shared/components/ui` (lo usan los tres módulos) y ahora
  también lo usa Notas de Venta: selector de "N por página", Anterior/Siguiente y
  "Mostrando X-Y de Z". El componente quedó desacoplado de los tipos del Módulo B.

Verificado contra Supabase: **8 comprobaciones, 0 fallas** (envoltorio correcto,
`page_size` respetado, páginas sin solapamiento, `total_pages` coherente, 422 para
`page_size=500` y `page=0`, y el filtro por fechas intacto). Suite del Módulo B:
**84 passed**. `tsc --noEmit` limpio.

> **Aparte**: `tests/modulo_d_documentos/test_domain.py` y `test_usecases.py` no
> compilan desde el commit `c081e8e` (importan `CanalNotificacion` y
> `generar_boleta_usecase`, eliminados en la reestructuración del Módulo D). Es
> anterior a estos cambios y queda para quien mantiene ese módulo.

---

## 11. Anexo — paginación en todo el sistema y aprobaciones a dos columnas (6ª pasada)

### 11.1 Los tres listados que faltaban
Mismo problema que Notas de Venta: el backend devolvía la colección completa y la
pantalla la acumulaba. Ahora los tres usan el envoltorio estándar
`{items, total, page, page_size, total_pages}` con `page_size` de 1 a 100 y
**LIMIT/OFFSET real en SQL** (no recorte en memoria):

| Endpoint | Antes | Ahora |
|---|---|---|
| `GET /ventas` | todas las ventas del rango | paginado (+ `GET /ventas/{id}` nuevo) |
| `GET /notificaciones` | toda la bandeja del usuario | paginado |
| `GET /respaldos` | todos los respaldos | paginado (había **78** en la BD de pruebas) |

Cambiar la forma de `GET /ventas` obligó a adaptar el proveedor del Módulo D
(`HttpVentaDataProvider`), que lo consumía como lista plana: ahora recorre las
páginas para el listado/ZIP de notas, y para buscar UNA venta usa el endpoint
nuevo `GET /ventas/{id}` en vez de recorrer el histórico entero (eran 3 métodos
haciendo scan lineal por cada nota generada).

En el frontend, `HistorialVentas`, `Notificaciones` y `Respaldos` usan el mismo
`PaginacionControles` que el resto.

### 11.2 Aprobaciones: el detalle se despliega en dos columnas
El detalle se abría en un modal que tapaba todo. Ahora la cola sigue siendo una
**tabla de filas a todo el ancho** y, al pedir el detalle, este se **despliega
debajo** en dos columnas:

- **Izquierda**: los productos por ingresar en una tabla propia —producto (con su
  código), cantidad, costo unitario y subtotal—, con la fila de totales
  (unidades y monto).
- **Derecha**: la boleta grande (fija al hacer scroll), con clic para abrirla en
  tamaño completo.

Así se contrasta lo declarado contra la boleta de un vistazo. Se elige una
solicitud tocando cualquier parte de su fila y la vista baja sola hasta el
detalle; los botones de aprobar/rechazar/editar quedan al pie del panel.

### Verificación
- Contra Supabase: **19 comprobaciones, 0 fallas** (envoltorio, `page_size`
  respetado, `total_pages` coherente, páginas sin solapamiento, 422 fuera de
  rango, notas de venta funcionando sobre el `/ventas` paginado y el nuevo
  `GET /ventas/{id}` con su 404).
- Suite del Módulo B: **84 passed**. `tsc --noEmit` limpio.
- Nota: `tests/modulo_c_ventas/` está vacío — el Módulo C no tiene tests propios,
  así que estos cambios se validaron con el script contra la BD real.

---

## 12. Anexo — reportes con datos reales y zona horaria del negocio (7ª pasada)

### 12.1 Los mockups de reportes
`infrastructure/dependencies.py` del Módulo D tenía dos proveedores inventados que
alimentaban `GET /reportes/resumen` y la exportación a Excel:

```python
class MockEgresosDataProvider:   # 1200 "Compra mercadería" + 150 luz + 80 agua
class MockMetodoPagoProvider:    # EFECTIVO 850, YAPE 320, PLIN 180, TARJETA 200
```

Reemplazados por consultas reales:

- **`SqlEgresosDataProvider`**: el egreso sale del **costo de la mercadería que
  entró**, o sea de las líneas (`detalle_solicitud`) de las solicitudes de
  ingreso **Aprobadas** — `SUM(cantidad × precio_compra_unitario)` — fechadas por
  `revisado_en` (cuándo impactó el inventario). Las pendientes y rechazadas no
  cuentan: no movieron ni stock ni plata.
- **`SqlMetodoPagoProvider`**: el desglose sale de `pagos_venta` (renglón por
  método, con su snapshot de código), no del resumen `ventas.metodo_pago`, que
  dice "MIXTO" cuando la venta se pagó con más de uno. Excluye las anuladas.

### 12.2 El bug que apareció verificando: todo el sistema fechaba en UTC
Al aprobar un ingreso a las 23:55 de Lima, el reporte del día NO lo contaba: la
BD guarda `timestamptz` y las consultas truncaban con `::date` en **UTC**, donde
ya era el día siguiente. Lo mismo pasaba con el filtro de fechas de `GET /ventas`
(`datetime.combine(..., tzinfo=timezone.utc)`), así que "las ventas de hoy" salían
incompletas todas las tardes-noche.

Se agregó `settings.zona_horaria_negocio` (`America/Lima` por defecto) y ahora el
día se calcula en esa zona: `(campo AT TIME ZONE :tz)::date` en los reportes y
límites de rango con `ZoneInfo` en el repositorio de ventas.

### Verificación
Contra Supabase: **8 comprobaciones, 0 fallas** — el resumen ya no devuelve los
montos del mock; una solicitud **pendiente** no suma egresos; al **aprobarla** el
egreso sube exactamente por su costo (4 × 250 = 1000); un rango sin movimientos da
0; más-vendidos y la exportación a Excel siguen funcionando.
Suite del Módulo B: **84 passed**. `tsc --noEmit` limpio.

### 12.3 Notificaciones: no hay ningún disparador
Revisado a pedido. El Módulo D tiene todo el andamiaje —tipos (`STOCK_BAJO`,
`APERTURA_CAJA`, `CIERRE_CAJA`, `SOLICITUD_INGRESO`, `SISTEMA`), envío a Telegram
y correo, configuración de nivel de detalle, bandeja y campanita— pero **nadie lo
llama**: `EnviarNotificacionUseCase` solo se ejecuta desde `POST /notificaciones`
(manual, solo ADMIN, y el frontend ni siquiera expone ese endpoint). Los módulos B
y C no mencionan notificaciones en ninguna línea, y en la BD no hay triggers para
esto (los únicos triggers son los de inmutabilidad de bitácora e historial de
precios). Las notificaciones que existen en la BD de pruebas son inserciones
manuales. **Cableado en la 8ª pasada (sección 13).**

---

## 13. Anexo — disparadores de notificaciones (8ª pasada)

El andamiaje del Módulo D ya existía; faltaba que alguien lo llamara. Se cableó
sin que B y C conozcan Telegram, correo ni la tabla `notificaciones`.

### El contrato
`modulo_d_documentos/notificador.py` expone `Notificador.avisar(...)`, que los
contenedores de B y C inyectan igual que ya inyectan la auditoría del Módulo A
(`contenedor_d.notificador(db)`). Regla central: **una notificación caída nunca
rompe la operación** — `avisar()` atrapa cualquier error y lo loguea, así que un
Telegram sin token no tumba una venta.

### Los cuatro eventos

| Evento | Dónde | Qué avisa |
|---|---|---|
| `SOLICITUD_INGRESO` | `RegistrarIngresoUseCase` (B) | El cajero registró un ingreso: productos, unidades y monto, pendiente de aprobación |
| `STOCK_BAJO` | `AjustarStockUseCase` (B) y `RegistrarVentaUseCase` (C) | El producto quedó en su mínimo o por debajo, con las unidades restantes |
| `APERTURA_CAJA` | `AbrirCajaUseCase` (C) | Quién abrió y con cuánto monto inicial |
| `CIERRE_CAJA` | `CerrarCajaUseCase` (C) | Vendido, efectivo esperado vs contado y **si hubo descuadre** |

Los cuatro van con `usuario_id=None`, es decir a la administradora: quedan en la
bandeja y además salen por Telegram y correo.

### La alerta de stock no se repite
`STOCK_BAJO` usa la marca `productos.alerta_stock_notificada` a través de un
**UPDATE condicional** (`... WHERE id = :id AND alerta_stock_notificada = FALSE`)
que devuelve si realmente cambió la fila. Así, dos ventas simultáneas que dejan el
mismo producto bajo mínimo generan **un solo aviso**, y el aviso se rearma solo
cuando el stock vuelve a superar el mínimo (al aprobar un ingreso o reponer por
devolución). Para eso `ProductoVendible` (Módulo C) ahora también trae
`stock_minimo`.

### Verificación
Contra Supabase: **11 comprobaciones, 0 fallas** — la solicitud del cajero
dispara su aviso; el ajuste que deja el producto en el mínimo dispara
`STOCK_BAJO`; un segundo ajuste **no** repite el aviso; tras reponer y volver a
bajar **sí** vuelve a avisar; abrir y cerrar caja disparan los suyos con el
detalle del arqueo; y una **venta** que deja el producto en su mínimo también
avisa (stock 3 → 2 con mínimo 2). Suite del Módulo B: **84 passed**.

---

## 14. Anexo — reportes que no mostraban nada y detalle en pop-up (9ª pasada)

### 14.1 El bug que dejaba los reportes en cero (regresión propia)
Al agregar la zona horaria del negocio (sección 12.2) usé `ZoneInfo("America/Lima")`
en el filtro de fechas de `GET /ventas`. **Windows no trae la base IANA de zonas
horarias**, así que sin el paquete `tzdata` eso levanta `ZoneInfoNotFoundError`:
el endpoint respondía 500, el proveedor del Módulo D se lo tragaba (devuelve `[]`
ante cualquier error) y el reporte mostraba **0 ventas, 0 productos vendidos y
ticket promedio 0**. Los egresos, que salen por SQL directo, sí funcionaban — de
ahí que el síntoma fuera parcial.

Corrección: `tzdata` declarado en `pyproject.toml` y `requirements.txt`, y un
helper `app/shared/config/zona_horaria.py` que degrada a UTC con un error claro en
el log si la zona no está disponible, en vez de tumbar el endpoint.

### 14.2 Ventas anuladas y devoluciones contaban como vendidas
Verificando lo anterior apareció que el resumen sumaba **todas** las ventas del
rango, incluidas las **ANULADAS** (que ya repusieron stock y devolvieron la plata),
y que el top de productos contaba unidades que habían vuelto al inventario por
**devoluciones parciales**. Ahora:

- Las ventas `ANULADA` se excluyen del total, del número de ventas y del top.
- Las cantidades se calculan netas (`cantidad − cantidad_devuelta`), tanto en el
  resumen como en `/reportes/mas-vendidos`.
- El resumen expone `total_devuelto` y el frontend lo muestra como indicador
  "Devoluciones"; el gráfico pasó a llamarse **"Cobrado por método de pago"**,
  porque sale de `pagos_venta` y es bruto. La relación queda cerrada y
  verificable: **cobrado = vendido + devoluciones**.

### 14.3 Aprobaciones: el detalle vuelve a ser pop-up
El detalle desplegado debajo obligaba a bajar la pantalla. Ahora abre en un
**pop-up ancho dividido en dos**: a la izquierda los productos por ingresar
(cantidad, costo unitario y subtotal) y a la derecha la boleta, sin scroll de
página y sin perder de vista ninguna de las dos.

### Verificación
Contra Supabase: **11 comprobaciones, 0 fallas** — la venta nueva suma y la
anulada no; el producto aparece en más vendidos con sus unidades; la devolución
parcial descuenta del producto y del total; `cobrado = vendido + devoluciones`;
el egreso sube por el costo del ingreso aprobado (+600); y la exportación a Excel
sigue funcionando. Suite del Módulo B: **84 passed**. `tsc --noEmit` limpio.

---

## 15. Anexo — paginación determinista: cada página con datos distintos (10ª pasada)

Revisión pedida sobre los listados: asegurar que la página 2 no repita ni
saltee filas de la página 1.

### 15.1 El problema: `ORDER BY` sobre columnas no únicas

Los 10 listados paginados hacían `LIMIT/OFFSET` ordenando por una columna
**que se repite**. Cuando hay filas empatadas, SQL **no garantiza** ningún
orden entre ellas: cada página se ordena por separado, así que la misma fila
puede caer en dos páginas y otra no aparecer nunca.

Los empates son reales en la BD de pruebas:

| Tabla | Filas | Filas empatadas | Ordenaba por |
|---|---|---|---|
| `productos` | 171 | **143** | `nombre` |
| `historial_precios` | 96 | 44 | `created_at` |
| `bitacora_auditoria` | 1015 | 10 | `created_at` |
| `respaldos` | 102 | 3 | `generado_en` |

`productos` es el caso grave, y es la tabla del **POS y del Catálogo**: hay 52
productos llamados `'P'`, 46 `'TestProd'` y 22 `'TestHist'`. Son datos de
prueba, pero el defecto es estructural — dos productos con el mismo nombre
alcanzan.

**Con el volumen actual el orden salía consistente**: forzando planes distintos
(sin índices, sort en disco) no se reprodujo la corrupción. Era un bug
**latente** — la garantía no existía y aparece al cambiar el plan o crecer los
datos.

### 15.2 La corrección

Desempate por PK (única) en el `ORDER BY` de los 10 listados paginados:

| Endpoint | ORDER BY ahora |
|---|---|
| `GET /bitacora` | `created_at DESC, id DESC` |
| `GET /movimientos` | `created_at DESC, id DESC` |
| `GET /productos/{id}/historial-precios` | `created_at DESC, id DESC` |
| `GET /productos` (POS + Catálogo) | `nombre, id` |
| `GET /productos/por-reponer` | `(stock_minimo - stock) DESC, nombre, id` |
| `GET /proveedores` | `razon_social, id` |
| `GET /proveedores/{id}/pagos` | `fecha DESC, created_at DESC, id DESC` |
| `GET /ingresos` | `created_at DESC, id DESC` |
| `GET /notificaciones` | `leida ASC, created_at DESC, id DESC` |
| `GET /respaldos` | `generado_en DESC, id DESC` |

`GET /ventas` ya ordenaba por `id DESC` — estaba bien.

### 15.3 Lo que el desempate NO arregla: el `OFFSET` se desplaza

Apareció verificando, y **es el hallazgo más importante**: si entran filas
entre dos requests, el `OFFSET` apunta a otro lado y el usuario ve una fila
repetida (o se saltea una). El desempate por PK no lo cubre — es inherente a
paginar por OFFSET sobre una tabla que se escribe.

Se reprodujo dos veces:

1. Insertando una fila entre cargar la página 1 y la 2 de bitácora (en una
   transacción revertida): 1 fila repetida, con y sin desempate.
2. **Sin querer**: dejando correr la suite de pytest contra la misma BD durante
   el barrido de verificación, `GET /proveedores` perdió filas y `GET /ingresos`
   las repitió. Con la BD quieta, los mismos listados dan OK.

O sea: **en producción, con el POS escribiendo mientras alguien pagina Ingresos
o Productos, esto pasa de verdad.** El arreglo de fondo es paginación por
cursor (keyset: `WHERE (created_at, id) < (:ultimo_created_at, :ultimo_id)`),
que no se hizo acá porque cambia el contrato de los 10 endpoints y del
`PaginacionControles` del frontend. Queda como recomendación.

### 15.4 `GET /notas-venta` paginaba en memoria — corregido

La sección 10 dice que se paginó en backend, pero sólo había cambiado la
**forma** de la respuesta: `notas_venta_router.py` seguía trayendo el histórico
completo vía HTTP (`listar_ventas` recorre todas las páginas de `/ventas`) y
recortaba con `ventas[inicio : inicio + page_size]`. Las páginas salían bien
(el orden de `/ventas` es `id DESC`, estable), pero cada request costaba lo
mismo que exportar el rango entero.

La paginación ahora baja hasta el origen:

* `VentaDataProviderPort.listar_ventas_paginado(desde, hasta, page, page_size)`
  → `(ventas de la página, total)`, con **una sola** llamada a `/ventas`.
* `listar_ventas` (el rango completo) se conserva porque hay tres consumidores
  que sí necesitan todo: los dos reportes y el ZIP de notas. Su docstring ahora
  dice explícitamente cuándo usar cada uno.

**Verificado** contra Supabase, instrumentando el adaptador:

| | Antes | Ahora |
|---|---|---|
| `GET /notas-venta?page=2` — recorridos del histórico completo | 1 | **0** |
| `GET /notas-venta?page=2` — llamadas paginadas a `/ventas` | 0 | **1** |
| `GET /reportes/resumen` — recorridos del histórico | 1 | 1 (sin cambio) |

Y el contrato intacto: `total=14` coincide con `/ventas`, páginas 1 y 2 sin
solapamiento, `page=0` y `page_size=500` siguen dando **422**.

### 15.5 Lo que ya estaba bien

* El frontend no pagina en memoria en ninguna pantalla (los `.slice()` que
  quedan son formato de fecha y topes de autocompletado).
* `PaginacionControles` de `modulo-b-inventario` es un re-export del de
  `shared/components/ui`, no un duplicado.
* Los listados sin paginar (`/categorias`, `/usuarios`, `/roles`, `/permisos`,
  `/metodos-pago`, `/caja/turnos`) son datos de referencia acotados.

### Verificación

Barrido página por página de los 11 listados, comparando la secuencia completa
de ids contra el listado traído de una sola vez, con **9 combinaciones de
`page_size` × plan de ejecución** cada uno (`page_size` 7/20/100 × plan normal /
sin índices / sort en disco), verificando además que no haya ids repetidos ni
faltantes:

**11 listados correctos, 0 con fallas** (con la BD sin escrituras concurrentes).

Suite del Módulo B: **84 passed**.

### 15.6 Los tests del Módulo D estaban desactualizados, no rotos

`tests/modulo_d_documentos/test_api.py` fallaba en **10 de 26**. Se comprobó con
`git stash` que fallaban igual sin los cambios de esta pasada, y al mirar cada
error resultó que **ninguno era un bug**: los 10 eran tests que quedaron
desactualizados respecto del código.

| Tests | Esperaban | Realidad | Causa |
|---|---|---|---|
| 5 de boletas | 401 / lista | **404** | Las boletas se eliminaron en la reestructuración (su reemplazo son las notas de venta) |
| `notificaciones_con_auth` | lista plana | envoltorio `{items, total, …}` | **La paginación de la 6ª pasada** (§11.1) |
| `respaldos_con_auth` | lista plana | envoltorio `{items, total, …}` | **La paginación de la 6ª pasada** (§11.1) |
| 2 de config notificaciones | `canal_telegram_activo`, `canal_correo_activo` | sólo `nivel_detalle` | Los canales salieron del schema |
| `drive_callback_sin_code` | 422 | 200 con `{"error": …}` | `code` es opcional a propósito: ahí aterriza el redirect de Google |

Vale marcar que **dos los rompió esta misma serie de revisiones**: al paginar
`/notificaciones` y `/respaldos` en la 6ª pasada se cambió la forma de la
respuesta sin actualizar sus tests.

Corregido: los 5 de boletas se reemplazaron por un test parametrizado que
verifica que las 4 rutas devuelven **404** (misma convención que se usó con las
mermas del Módulo B), y los otros 5 se alinearon con el contrato actual.
Resultado: **25 passed**.

> **Pendiente**: `test_domain.py` y `test_usecases.py` siguen sin compilar
> (importan `CanalNotificacion` y `generar_boleta_usecase`, ambos eliminados).
> Se dejan como están por decisión del equipo: van a reescribirse cuando se
> encare la cobertura de tests completa del sistema.

---

## 16. Anexo — paginación por cursor en los listados que se escriben (11ª pasada)

La 10ª pasada dejó pendiente lo único que el desempate por PK **no** arregla:
el `OFFSET` cuenta posiciones sobre los datos del momento, así que si entran
filas mientras alguien navega, las páginas se corren y se ven registros
repetidos (o se saltean).

### 16.1 Sólo tres listados lo necesitan

El desfase aparece donde el orden es por **fecha de inserción descendente** y
las filas nuevas caen arriba:

| Listado | Ordena por | ¿Se escribe mientras se navega? |
|---|---|---|
| `GET /bitacora` | `created_at DESC` | **Sí**, cada request se audita |
| `GET /inventario/movimientos` | `created_at DESC` | **Sí**, cada venta escribe |
| `GET /ingresos` | `created_at DESC` | **Sí**, los cajeros registran |
| `GET /productos` | `nombre, id` | **No** — vender cambia `stock`, no el nombre |
| Proveedores, pagos, respaldos, notificaciones | — | casi no cambian |

**Productos quedó afuera a propósito**: su clave de orden es estable, así que
una venta no le mueve la posición a ningún producto. Sólo se desplaza al crear
o renombrar productos, que es una acción ocasional del admin.

### 16.2 Cómo quedó

`app/shared/http/cursor.py` codifica el par `(created_at, id)` en base64url.
Es opaco para el cliente, así que el formato se puede cambiar sin romper nada,
y un cursor corrupto da **422** (llega por querystring: cualquiera puede mandar
cualquier cosa).

En SQL, `OFFSET` se reemplaza por la comparación de tuplas, que usa el mismo
índice que el `ORDER BY`:

```sql
WHERE (created_at, id) < (:cursor_fecha, :cursor_id)
ORDER BY created_at DESC, id DESC LIMIT :n
```

**No es un cambio incompatible**: los tres endpoints siguen aceptando `page` /
`pagina`. Si viene `cursor` se usa keyset, si no, OFFSET como antes.

### 16.3 El frontend no cambió de aspecto

Los controles ya eran sólo *Anterior / Siguiente* —nunca hubo saltar a la
página 7—, así que **no se perdió nada de la UI**: se conservan el selector de
"N por página", el "Mostrando X-Y de Z" y el "Pág. N / M" (el `total` se sigue
calculando).

Lo que cambia es de dónde sale la página: `shared/lib/use-paginacion-cursor.ts`
mantiene una pila de cursores y traduce los ±1 del control a avanzar o
retroceder. `PaginacionControles` **no se tocó**. La bitácora administra su pila
dentro de `useBitacora`, porque ahí los filtros ya vivían en el hook.

Al cambiar cualquier filtro o el tamaño de página se descartan los cursores: son
otro conjunto de resultados y los cortes viejos no aplican.

### Verificación

Insertando una fila entre página y página (todo en transacciones revertidas,
salvo lo indicado abajo):

| Tabla | OFFSET | Cursor |
|---|---|---|
| `bitacora_auditoria` | **ROTO** — 5 filas repetidas | **OK** — 0 |
| `movimientos_inventario` | **ROTO** — 4 filas repetidas | **OK** — 0 |
| `solicitudes_ingreso` | **ROTO** — 4 filas repetidas | **OK** — 0 |

Además, contra Supabase: los tres listados recorren sus páginas sin repetidos,
volver atrás con el cursor guardado devuelve exactamente la misma página, y un
cursor inválido da 422 en los tres. `tsc --noEmit` limpio.

Suites: Módulo B **84 passed**; Módulo A **13 passed, 1 failed**
(`test_bloqueo_tras_tres_intentos_fallidos`, sobre el bloqueo por intentos de
login). Se verificó con `git stash` que **falla igual sin estos cambios**: es
preexistente y ajeno a la paginación.

> **Nota sobre datos**: verificando la bitácora se insertaron **24 filas con
> `accion='PROBE_CURSOR'`** (ids 1099-1122) antes de darnos cuenta de que la
> tabla es inmutable por trigger y no admite `DELETE`. Quedan ahí, marcadas y
> filtrables. Las pruebas siguientes se hicieron dentro de transacciones que se
> revierten, que es como debió hacerse desde el principio.

---

## 17. Anexo — esquema definitivo de la BD (12ª pasada)

Se revisó el modelo E-R contra el código y se generó `db/schema.sql`, el
esquema **definitivo y único**, pensado para recrear la base desde cero.

### 17.1 El bug que apareció revisando: el respaldo dejaba 7 tablas afuera

`crear_respaldo_usecase.py` tenía una lista fija `TABLAS_ORDEN` que se había
quedado vieja. Como `tablas_a_volcar` la filtra por las tablas que existen, no
fallaba: **omitía en silencio**.

No se estaban respaldando `proveedores`, `solicitudes_ingreso`,
`detalle_solicitud`, `pagos_proveedor`, `movimientos_inventario`,
`historial_precios` ni `mermas` — todo el lado de proveedores, ingresos y
movimientos de inventario. Y además listaba `clientes`, `fiados` y `abonos`,
que ya no existen. Corregido y anotado en el propio archivo.

### 17.2 Estado real: la BD no estaba tan sucia

Las 28 tablas de Supabase coinciden **exactamente** con los modelos: no hay
tablas huérfanas ni columnas que el código espere y no existan. La única
columna sin mapear era `productos.foto_url`.

Lo que sí sobraba: **`mermas`** (22 columnas, 6 FKs, 4 índices) sin ningún
código que la usara, y **5 permisos huérfanos** (`mermas.registrar`,
`mermas.confirmar` y los tres del fiado).

### 17.3 Qué se eliminó

* Tabla `mermas`, `movimientos_inventario.merma_id` y el tipo de movimiento
  `'merma'`. Con ellos se fueron `MermaModel`, la factory muerta
  `MovimientoInventario.merma()`, el VO `TipoMovimiento.MERMA`, el filtro del
  frontend y los campos de los schemas. El reemplazo sigue siendo el ajuste
  manual de stock, que ahora tiene su propio CHECK: `chk_mov_ajuste_tiene_motivo`
  (un ajuste sin motivo no entra: es la única trazabilidad del faltante).
* `productos.foto_url` y los 5 permisos huérfanos.
* Los 4 `db/schema_modulo_*.sql` y `limpieza_ventas_fiado.sql`, reemplazados
  por `db/schema.sql`.

### 17.4 Mejoras de estructura aplicadas

| # | Problema | Corrección |
|---|---|---|
| 1 | `productos.codigo` y `categorias.nombre` eran únicos **globales**: un registro dado de baja quemaba su código para siempre (41 de 183 productos borrados) | Índice único **parcial** `WHERE deleted_at IS NULL`, mismo criterio que `proveedores.ruc` |
| 2 | `productos.creado_por`, `actualizado_por`, `categorias.creado_por`, todos los `deleted_by` y `notificaciones.producto_id` eran enteros sueltos, sin FK | FK a `usuarios`/`productos`, unificando el criterio con las que sí la tenían |
| 3 | Índices duplicados: `ix_productos_codigo` + `productos_codigo_key`, e igual en `usuarios.username` y `proveedores.ruc` | Se deja solo el del UNIQUE |
| 4 | Los índices no acompañaban al `ORDER BY (created_at DESC, id DESC)` de la paginación por cursor | Compuestos en bitácora, movimientos, solicitudes, historial, notificaciones y respaldos. Además `detalles_venta(producto_id)`, que faltaba y lo usan los reportes |

### 17.5 Reportes: "más vendidos" agrupaba por nombre

Salió mientras se evaluaba el punto 1: `generar_reporte_mas_vendidos_usecase`
agrupaba por el **nombre** del producto, así que dos productos distintos que se
llamaran igual se sumaban como uno solo. Ahora agrupa por `producto_id` y el
nombre se usa sólo para mostrar — tomando el de la venta más reciente
(comparando por id de venta, sin depender del orden en que lleguen).

### 17.6 Alembic

Las 20 migraciones se colapsaron en `0001_esquema_inicial`, que ejecuta
`db/schema.sql`. Se terminan de raíz los dos *heads*, la revisión huérfana
`0013_modulo_d_respaldo_drive` (aplicada en la BD compartida pero inexistente
en la rama) y las migraciones que hacían `ALTER` sobre tablas que ninguna
creaba. `alembic heads` → **una sola cabeza**.

`scripts/aplicar_schema.py` ahora aplica `db/schema.sql` y **aborta si la base
ya tiene tablas**, salvo que se pase `--reset`.

### Verificación

El script se ejecutó completo contra Postgres real en un esquema temporal que
se revierte (la BD quedó intacta), comprobando:

* **26 tablas creadas == 26 modelos** SQLAlchemy, y columna por columna.
* Seed cargado: 2 roles, 25 permisos, admin, 5 métodos de pago y las 2 filas
  de configuración.
* Los **25 permisos que el código exige** (`require_permission`) están todos, y
  ADMIN los tiene todos.
* El seed coincide **exactamente** con `scripts/seed.py`, permiso por permiso,
  incluidos los 9 del CAJERO.
* `admin` / `admin123` valida contra el hasher de la aplicación y entra con
  `debe_cambiar_password = TRUE`.

> **Se detectó a tiempo**: el hash bcrypt del admin se había escrito de memoria
> y era **inválido** — habría dejado el sistema sin acceso. Se reemplazó por uno
> generado y verificado contra `BcryptPasswordHasher`.

### 17.7 Cómo recrear la base

```bash
# Opción A — script directo (borra todo y recrea)
python -m scripts.aplicar_schema --reset

# Opción B — alembic (equivalente: la migración inicial ejecuta el mismo SQL)
alembic upgrade head
```
