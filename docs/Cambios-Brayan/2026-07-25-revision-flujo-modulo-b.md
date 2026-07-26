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

