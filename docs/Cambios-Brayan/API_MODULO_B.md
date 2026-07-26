# Módulo B — API REST y Contratos

> Especificación de la **capa HTTP** del Módulo B y de los **contratos** con el Módulo C (Ventas) y con el frontend.
> Autor: Brayan. Mantenedor: equipo Módulo B.
> Versión: 1.1. (PR2: lógica de catálogo, inventario, ingresos, mermas, proveedores y storage implementada).

## 1. Introducción

Este documento describe:

1. Los **endpoints HTTP REST** que el Módulo B expone **para el frontend** (no para el Módulo C).
2. El **contrato técnico con el Módulo C**, que se materializa como **acceso SQL directo a la tabla `productos`**, no como HTTP (decisión de RNF-03).
3. El **contrato con el frontend** ya implementado en `frontend/src/modules/modulo-b-inventario/services/*.port.ts` (fuente de verdad de las pantallas).

### 1.1 Base URL y autenticación

- **Base URL local**: `http://localhost:8000` (FastAPI en `backend/app/main.py`).
- **Base URL producción**: según `docs/DESPLIEGUE.md` (Cloud Run / contenedor).
- **Documentación interactiva**: `GET /docs` (Swagger UI) y `GET /redoc` (Redoc) — generados por FastAPI.
- **Autenticación**: **JWT en header `Authorization: Bearer <token>`**. El token lo emite el Módulo A (`POST /auth/login`). La validación la hace el middleware de A (`get_current_user` en `API_MODULO_A.md`).
- **Errores**: todas las respuestas de error siguen el formato `{"detail": "mensaje en español"}` con códigos HTTP estándar. Ver sección 8.

### 1.2 Convenciones de la API

- **Prefijos** por recurso:
  - `/productos` — productos.
  - `/categorias` — categorías.
  - `/ingresos` — solicitudes de ingreso (flujo de aprobación).
  - `/mermas` — mermas y pérdidas.
  - `/proveedores` — proveedores y deudas.
  - `/inventario/movimientos` — bitácora de movimientos.
  - `/storage` — subida de archivos (foto de boleta, foto de producto).
- **Paginación**: query params `page` (1-based, default 1) y `page_size` (default 20, max 100).
- **Filtros**: query params adicionales según el recurso. Documentados por endpoint.
- **Soft delete**: ningún endpoint expone registros con `deleted_at IS NOT NULL` salvo que se pida explícitamente (ej. auditoría).
- **Idioma**: mensajes de error y descripciones en español. Identificadores y campos en `snake_case` (consistente con el backend Python).
- **Fechas**: ISO 8601 con zona horaria (`2026-07-19T15:30:00-03:00`).
- **Montos**: serializados como `string` con 2 decimales en JSON (consistente con el estándar de NUMERIC en Pydantic/SQLAlchemy).
- **Timestamps**: serializados como string ISO 8601.

### 1.3 Permisos

Los permisos se validan en el backend con el middleware del Módulo A (`require_permission(...)`). La siguiente tabla resume la matriz; cada endpoint repite la columna **Permiso**. Ver `API_MODULO_A.md` para los códigos de permiso exactos.

| Recurso | Acción | ADMIN | CAJERO |
|---|---|---|---|
| `/productos` | GET listado y búsqueda | ✅ | ✅ |
| `/productos` | GET por id | ✅ | ✅ |
| `/productos` | POST alta | ✅ | ❌ |
| `/productos` | PATCH edición general | ✅ | ❌ |
| `/productos/{id}/precio` | PATCH cambio de precio | ✅ | ❌ |
| `/productos/{id}/historial-precios` | GET | ✅ | ❌ |
| `/productos/por-reponer` | GET | ✅ | ✅ |
| `/categorias` | GET | ✅ | ✅ |
| `/categorias` | POST | ✅ | ❌ |
| `/categorias` | PATCH | ✅ | ❌ |
| `/ingresos` | POST crear solicitud | ✅ | ✅ |
| `/ingresos` | GET listado/detalle | ✅ | ✅ (solo propias) |
| `/ingresos/{id}/aprobar` | POST | ✅ | ❌ |
| `/ingresos/{id}/rechazar` | POST | ✅ | ❌ |
| `/mermas` | POST (registrar, paso 1) | ✅ | ✅ (D-14) |
| `/mermas` | GET | ✅ | ❌ |
| `/mermas/{id}/confirmar` | POST (paso 2) | ✅ | ❌ |
| `/mermas/{id}/rechazar` | POST (paso 2) | ✅ | ❌ |
| `/proveedores` | GET | ✅ | ❌ |
| `/proveedores` | POST | ✅ | ❌ |
| `/proveedores` | PATCH | ✅ | ❌ |
| `/proveedores/{id}/compras-credito` | POST | ✅ | ❌ |
| `/proveedores/{id}/pagos` | POST | ✅ | ❌ |
| `/proveedores/{id}/pagos` | GET (historial) | ✅ | ❌ |
| `/inventario/movimientos` | GET | ✅ | ✅ (filtros) |

---

## 2. Endpoints — Productos

### 2.1 `POST /productos` — Alta de producto (CU-B01)

**Permiso**: `ADMIN`.

**Body** (JSON):
```json
{
  "codigo": "7750123456789",
  "nombre": "Coca-Cola 500ml",
  "categoria_id": 3,
  "precio_venta": 3.50,
  "precio_compra_actual": 2.20,
  "stock_minimo": 10,
  "es_codigo_interno": false,
  "foto_url": "https://storage.example.com/productos/cc-500.jpg"
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `codigo` | string (3-60) | ✅ | UNIQUE en `productos.codigo`. Si `es_codigo_interno=true`, formato `PREFIJO-CORRELATIVO` validado por regex. |
| `nombre` | string (1-150) | ✅ | — |
| `categoria_id` | int | ✅ | FK existente, `deleted_at IS NULL`. |
| `precio_venta` | number | ✅ | `>= 0`. Se persiste en `productos.precio` (compatibilidad con Módulo C). |
| `precio_compra_actual` | number | ✅ | `>= 0`. |
| `stock_minimo` | int | opcional | default 0. `>= 0`. |
| `es_codigo_interno` | bool | opcional | default `false`. |
| `foto_url` | string (URL) | opcional | — |

**Respuesta OK** (201 Created):
```json
{
  "id": 142,
  "codigo": "7750123456789",
  "nombre": "Coca-Cola 500ml",
  "categoria_id": 3,
  "categoria_nombre": "Bebidas",
  "precio": 3.50,
  "precio_compra_actual": 2.20,
  "stock": 0,
  "stock_minimo": 10,
  "activo": true,
  "es_codigo_interno": false,
  "foto_url": "https://storage.example.com/productos/cc-500.jpg",
  "created_at": "2026-07-19T15:30:00-03:00",
  "created_by": 1,
  "created_by_nombre": "María (Admin)"
}
```

**Errores**:
- `409` — código duplicado (`{"detail": "Ya existe un producto con ese código"}`).
- `404` — categoría inexistente.
- `422` — validación de campos (precio negativo, código mal formado, etc.).
- `403` — sin permiso.

**Efecto colateral**: `INSERT` en `historial_precios` con `precio_anterior=NULL`, `precio_nuevo=precio_venta`, `tipo_precio='venta'`.

### 2.2 `GET /productos` — Listado paginado (CU-B08)

**Permiso**: `ADMIN` y `CAJERO`.

**Query params**:
| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `page` | int | 1 | Página (1-based). |
| `page_size` | int | 20 | Items por página (max 100). |
| `search` | string | — | Filtro por `nombre` (case-insensitive, `ILIKE`). |
| `categoria_id` | int | — | Filtro por categoría. |
| `solo_con_stock` | bool | false | Si `true`, solo `stock > 0`. |
| `solo_bajo_minimo` | bool | false | Si `true`, solo `stock <= stock_minimo`. |
| `activo` | bool | — | Filtra por `activo`. Si no se manda, devuelve todos. |

**Respuesta OK** (200):
```json
{
  "items": [
    {
      "id": 142,
      "codigo": "7750123456789",
      "nombre": "Coca-Cola 500ml",
      "categoria_id": 3,
      "categoria_nombre": "Bebidas",
      "precio": 3.50,
      "stock": 47,
      "stock_minimo": 10,
      "activo": true,
      "es_codigo_interno": false
    }
  ],
  "total": 248,
  "page": 1,
  "page_size": 20,
  "total_pages": 13
}
```

**Errores**: `422` (validación de params).

### 2.3 `GET /productos/buscar` — Búsqueda por código o nombre (CU-B02, CU-B03)

**Permiso**: `ADMIN` y `CAJERO`.

**Query params** (al menos uno requerido):
| Param | Tipo | Descripción |
|---|---|---|
| `codigo` | string | Búsqueda exacta por código. Usado por el POS al escanear. |
| `nombre` | string (min 2 chars) | Búsqueda parcial. Usado por el buscador del POS. |
| `categoria_id` | int (opcional) | Filtro adicional cuando se busca por nombre. |
| `limit` | int (default 20, max 50) | Límite de resultados. |

**Lógica de búsqueda**:
- Si viene `codigo` → búsqueda exacta con índice UNIQUE. Retorna 1 producto o 404.
- Si viene `nombre` → búsqueda `ILIKE %nombre%` con índice `idx_productos_nombre`. Retorna hasta `limit` productos.
- Si vienen ambos → `codigo` tiene prioridad.

**Respuesta OK** (200): misma forma que un item de `/productos` (o array si fue por nombre).

**Errores**:
- `404` — código no encontrado.
- `422` — sin parámetros, o `nombre` con < 2 chars.

**Rendimiento objetivo (RNF-02)**: < 1 segundo en condiciones normales. La búsqueda por código debe ser < 100 ms (índice B-tree único).

### 2.4 `GET /productos/{id}` — Detalle

**Permiso**: `ADMIN` y `CAJERO`.

**Respuesta OK** (200): mismo objeto que el alta, con todos los campos.

**Errores**: `404` (no existe o está borrado lógicamente).

### 2.5 `PATCH /productos/{id}` — Edición general

**Permiso**: `ADMIN`.

**Body**: cualquiera de los campos editables, con la misma validación que el alta. **No permite** cambiar `precio` ni `precio_compra_actual` por esta vía; para eso usar `PATCH /productos/{id}/precio` (CU-B10).

**Respuesta OK** (200): producto actualizado.

**Errores**: `404`, `409` (código duplicado), `422`, `403`.

### 2.6 `PATCH /productos/{id}/precio` — Cambiar precio (CU-B10)

**Permiso**: `ADMIN` (**exclusivo**, validación en backend).

**Body**:
```json
{
  "precio_venta": 3.75,
  "precio_compra_actual": 2.30
}
```

Ambos campos son opcionales; al menos uno debe estar presente. Si un campo no se incluye, mantiene su valor actual.

**Comportamiento** (transaccional):
1. Por cada precio que cambió, `INSERT` en `historial_precios` con `precio_anterior` (el valor previo) y `precio_nuevo`.
2. `UPDATE productos SET precio = ..., precio_compra_actual = ..., updated_at = now()`.
3. Si ningún precio cambió, no se inserta fila de historial.

**Respuesta OK** (200): producto actualizado, con un campo extra `historial_registrado: true|false`.

**Errores**:
- `403` — rol `CAJERO` intentando (aunque la UI lo oculte).
- `404` — producto inexistente.
- `422` — precio negativo.

### 2.7 `GET /productos/{id}/historial-precios` — Historial (CU-B14)

**Permiso**: `ADMIN`.

**Query params**:
| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `tipo` | string | — | Filtro: `venta` o `compra`. Si se omite, ambos. |
| `page` | int | 1 | — |
| `page_size` | int | 20 | max 100. |

**Respuesta OK** (200):
```json
{
  "items": [
    {
      "id": 512,
      "fecha": "2026-07-15T10:00:00-03:00",
      "precio_anterior": 3.50,
      "precio_nuevo": 3.75,
      "tipo_precio": "venta",
      "modificado_por": 1,
      "modificado_por_nombre": "María (Admin)"
    },
    {
      "id": 87,
      "fecha": "2026-05-20T14:30:00-03:00",
      "precio_anterior": null,
      "precio_nuevo": 3.50,
      "tipo_precio": "venta",
      "modificado_por": 1,
      "modificado_por_nombre": "María (Admin)"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

**Errores**: `404`, `422`, `403`.

### 2.8 `GET /productos/por-reponer` — Alerta stock mínimo (CU-B11)

**Permiso**: `ADMIN` y `CAJERO`.

**Query params**:
| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `categoria_id` | int | — | Filtro por categoría. |
| `page` | int | 1 | — |
| `page_size` | int | 20 | max 100. |

**Respuesta OK** (200):
```json
{
  "items": [
    {
      "id": 87,
      "codigo": "7750000111222",
      "nombre": "Galletas Soda",
      "categoria_id": 5,
      "categoria_nombre": "Snacks",
      "stock": 2,
      "stock_minimo": 10,
      "faltante": 8
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20
}
```

`faltante = stock_minimo - stock`. Ordenado por `faltante DESC`.

**Errores**: `422`.

---

## 3. Endpoints — Categorías

### 3.1 `GET /categorias` — Listado

**Permiso**: `ADMIN` y `CAJERO`.

**Respuesta OK** (200):
```json
{
  "items": [
    { "id": 1, "nombre": "Bebidas" },
    { "id": 2, "nombre": "Snacks" }
  ],
  "total": 12
}
```

### 3.2 `POST /categorias` — Alta

**Permiso**: `ADMIN`.

**Body**: `{ "nombre": "Limpieza" }`.

**Respuesta OK** (201): `{ "id": 13, "nombre": "Limpieza" }`.

**Errores**: `409` (nombre duplicado), `422`.

### 3.3 `PATCH /categorias/{id}` — Edición

**Permiso**: `ADMIN`.

**Body**: `{ "nombre": "Limpieza del Hogar" }`.

**Errores**: `404`, `409`, `422`.

---

## 4. Endpoints — Ingresos / Solicitudes

> Esta es la pieza más sensible del módulo: implementa el flujo de dos pasos (CU-B04 → CU-B05/CU-B06). El stock **no se toca** hasta que el ADMIN aprueba.

### 4.1 `POST /ingresos` — Crear solicitud de ingreso (CU-B04)

**Permiso**: `ADMIN` y `CAJERO`.

**Body** (multipart/form-data o JSON con URL de foto):
```json
{
  "proveedor_id": 4,
  "foto_boleta_url": "https://storage.example.com/boletas/2026-07-19-001.jpg",
  "lineas": [
    {
      "producto_id": 142,
      "cantidad": 24,
      "precio_compra_unitario": 2.20
    },
    {
      "producto_id": 87,
      "cantidad": 12,
      "precio_compra_unitario": 0.80
    }
  ]
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `proveedor_id` | int | opcional | FK existente o `null`. |
| `foto_boleta_url` | string (URL) | ✅ | **Obligatoria**. Validación 422 si falta. |
| `lineas` | array | ✅ | Mínimo 1 línea. Cada línea: `producto_id` (FK existente), `cantidad > 0`, `precio_compra_unitario >= 0`. |

**Comportamiento** (transaccional):
1. `INSERT` en `solicitudes_ingreso` con `estado='Pendiente'`, `solicitado_por` (de JWT), `solicitado_por_nombre` (snapshot).
2. `INSERT` en `detalle_solicitud` por cada línea.
3. **No se toca `productos.stock`**.

**Respuesta OK** (201):
```json
{
  "id": 27,
  "estado": "Pendiente",
  "proveedor_id": 4,
  "proveedor_nombre": "Distribuidora Lima SAC",
  "foto_boleta_url": "https://storage.example.com/boletas/2026-07-19-001.jpg",
  "lineas": [
    {
      "id": 51,
      "producto_id": 142,
      "producto_nombre": "Coca-Cola 500ml",
      "cantidad": 24,
      "precio_compra_unitario": 2.20
    },
    {
      "id": 52,
      "producto_id": 87,
      "producto_nombre": "Galletas Soda",
      "cantidad": 12,
      "precio_compra_unitario": 0.80
    }
  ],
  "created_at": "2026-07-19T15:30:00-03:00",
  "solicitado_por": 2,
  "solicitado_por_nombre": "Juan (Cajero)"
}
```

**Errores**:
- `422` — sin foto, sin líneas, validación de líneas.
- `404` — `proveedor_id` o `producto_id` inexistente.
- `403` — sin permiso.

### 4.2 `GET /ingresos` — Listado de solicitudes (CU-B07)

**Permiso**: `ADMIN` ve todas; `CAJERO` ve solo las propias.

**Query params**:
| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `estado` | string | — | Filtro: `Pendiente` / `Aprobada` / `Rechazada`. |
| `proveedor_id` | int | — | Filtro por proveedor. |
| `fecha_desde` | date | — | `created_at >= fecha_desde`. |
| `fecha_hasta` | date | — | `created_at <= fecha_hasta`. |
| `page` | int | 1 | — |
| `page_size` | int | 20 | max 100. |

**Respuesta OK** (200):
```json
{
  "items": [
    {
      "id": 27,
      "estado": "Pendiente",
      "proveedor_id": 4,
      "proveedor_nombre": "Distribuidora Lima SAC",
      "cantidad_productos": 2,
      "monto_total": 62.40,
      "foto_boleta_url": "https://...",
      "created_at": "2026-07-19T15:30:00-03:00",
      "solicitado_por": 2,
      "solicitado_por_nombre": "Juan (Cajero)",
      "revisado_por": null,
      "revisado_en": null
    }
  ],
  "total": 14,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 4.3 `GET /ingresos/{id}` — Detalle

**Permiso**: `ADMIN` o dueño de la solicitud.

**Respuesta OK** (200): la solicitud completa con todas las líneas y snapshots.

**Errores**:
- `404` — no existe.
- `403` — el cajero intenta ver una solicitud ajena.

### 4.4 `POST /ingresos/{id}/aprobar` — Aprobar (CU-B05)

**Permiso**: `ADMIN` (**exclusivo**).

**Body** (opcional): permite ajustes finales:
```json
{
  "ajustes_lineas": [
    { "id": 51, "cantidad": 24, "precio_compra_unitario": 2.20 },
    { "id": 52, "cantidad": 10, "precio_compra_unitario": 0.80 }
  ]
}
```

Si no se manda `ajustes_lineas`, se aprueban las líneas originales.

**Comportamiento** (transaccional — RNF-03):
1. `SELECT ... FOR UPDATE` sobre la solicitud. Verifica `estado='Pendiente'`. Si no → 409.
2. `UPDATE solicitudes_ingreso SET estado='Aprobada', revisado_por=:admin, revisado_por_nombre=:nombre, revisado_en=now(), updated_at=now() WHERE id=:id AND estado='Pendiente'`. Si `rowcount=0` → 409.
3. Por cada `detalle_solicitud` (con ajustes si los hay):
   - `UPDATE productos SET stock = stock + :cantidad, updated_at = now() WHERE id = :producto_id AND deleted_at IS NULL`. Si `rowcount=0` → ROLLBACK → 409 con detalle del producto.
   - `INSERT` en `movimientos_inventario` con `tipo='ingreso'`, `cantidad=+:cantidad`, `solicitud_ingreso_id=:id`, `registrado_por` y nombre del admin.
4. `COMMIT`.

**Respuesta OK** (200):
```json
{
  "id": 27,
  "estado": "Aprobada",
  "revisado_por": 1,
  "revisado_por_nombre": "María (Admin)",
  "revisado_en": "2026-07-19T16:00:00-03:00",
  "productos_actualizados": 2,
  "unidades_agregadas": 34
}
```

**Errores**:
- `403` — rol `CAJERO`.
- `404` — solicitud inexistente.
- `409` — solicitud ya revisada / producto borrado lógicamente entre la creación y la aprobación.
- `422` — ajustes inválidos.

### 4.5 `POST /ingresos/{id}/rechazar` — Rechazar (CU-B06)

**Permiso**: `ADMIN` (**exclusivo**).

**Body**:
```json
{
  "motivo_rechazo": "El precio unitario no coincide con la boleta adjunta."
}
```

**Comportamiento**:
1. Verifica `estado='Pendiente'`. Si no → 409.
2. `UPDATE solicitudes_ingreso SET estado='Rechazada', motivo_rechazo=:motivo, revisado_por=:admin, revisado_por_nombre=:nombre, revisado_en=now() WHERE id=:id AND estado='Pendiente'`.
3. **No se toca `productos.stock`**.

**Respuesta OK** (200): solicitud rechazada con detalle.

**Errores**: `403`, `404`, `409`, `422` (motivo vacío o < 5 chars).

---

## 5. Endpoints — Mermas (CU-B09, CU-B09b, CU-B09c)

> Flujo de validación en dos pasos (D-14). El reporte (paso 1) no toca stock; la confirmación o rechazo (paso 2) sí lo hace (solo la confirmación).

### 5.1 `POST /mermas` — Reportar merma (paso 1, estado `Registrada`)

**Permiso**: `ADMIN` y `CAJERO` (D-14).

**Body**:
```json
{
  "producto_id": 142,
  "cantidad": 3,
  "motivo": "vencimiento",
  "observacion": "Vencen el 2026-07-15",
  "proveedor_id": 4
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `producto_id` | int | ✅ | FK existente, no borrado lógicamente. |
| `cantidad` | int | ✅ | `> 0`. **No se valida contra el stock** en este paso. |
| `motivo` | string | ✅ | Uno de: `vencimiento`, `rotura`, `otro`. |
| `observacion` | string | opcional | — |
| `proveedor_id` | int | opcional | FK existente o `null`. |

**Comportamiento**:
1. `INSERT` en `mermas` con `estado='Registrada'`, snapshots del registrador.
2. **No se toca `productos.stock`**. **No se crea `movimiento_inventario`**.

**Respuesta OK** (201):
```json
{
  "id": 33,
  "producto_id": 142,
  "producto_nombre": "Coca-Cola 500ml",
  "cantidad": 3,
  "motivo": "vencimiento",
  "observacion": "Vencen el 2026-07-15",
  "proveedor_id": 4,
  "estado": "Registrada",
  "motivo_rechazo": null,
  "created_at": "2026-07-19T15:30:00-03:00",
  "registrado_por": 2,
  "registrado_por_nombre": "Juan (Cajero)",
  "confirmado_por": null,
  "rechazado_por": null
}
```

**Errores**: `403`, `404`, `422`.

### 5.2 `GET /mermas` — Listado

**Permiso**: `ADMIN`.

**Query params**: `estado` (default: todas; valores: `Registrada`/`Confirmada`/`Rechazada`), `motivo`, `producto_id`, `fecha_desde`, `fecha_hasta`, `page`, `page_size`.

**Respuesta OK** (200): lista paginada con `id`, `fecha`, `producto`, `cantidad`, `motivo`, `observacion`, `proveedor`, `estado`, `registrado_por`, `confirmado_por` o `rechazado_por`.

### 5.3 `GET /mermas/{id}` — Detalle

**Permiso**: `ADMIN`.

**Respuesta OK** (200): merma completa con todos los snapshots y, si fue confirmada o rechazada, los datos del ADMIN que decidió.

### 5.4 `POST /mermas/{id}/confirmar` — Confirmar merma (paso 2, descuenta stock)

**Permiso**: `ADMIN` (**exclusivo**, D-14).

**Body**: vacío.

**Comportamiento** (transaccional, RNF-03):
1. `SELECT ... FOR UPDATE` sobre la merma. Verifica `estado='Registrada'`. Si no → 409.
2. `UPDATE mermas SET estado='Confirmada', confirmado_por=:admin, confirmado_por_nombre=:nombre, confirmado_en=now() WHERE id=:id AND estado='Registrada'`. Si `rowcount=0` → 409.
3. `INSERT` en `movimientos_inventario` con `tipo='merma'`, `cantidad=-:cantidad`, `merma_id=:merma.id`, `motivo = mermas.motivo`, snapshots del admin.
4. `UPDATE productos SET stock = stock - :cantidad, updated_at = now() WHERE id = :producto_id AND stock >= :cantidad AND deleted_at IS NULL`. Si `rowcount = 0` → ROLLBACK → 409 *"Stock insuficiente"*.
5. `COMMIT`.

**Respuesta OK** (200):
```json
{
  "id": 33,
  "estado": "Confirmada",
  "confirmado_por": 1,
  "confirmado_por_nombre": "María (Admin)",
  "confirmado_en": "2026-07-19T16:00:00-03:00",
  "stock_actualizado": 44
}
```

**Errores**:
- `403` — rol `CAJERO`.
- `404` — merma inexistente.
- `409` — merma ya confirmada/rechazada, o stock insuficiente al momento de confirmar.

### 5.5 `POST /mermas/{id}/rechazar` — Rechazar merma (paso 2, sin tocar stock)

**Permiso**: `ADMIN` (**exclusivo**, D-14).

**Body**:
```json
{
  "motivo_rechazo": "El producto aún está vigente, no corresponde merma por vencimiento."
}
```

**Comportamiento**:
1. Verifica `estado='Registrada'`. Si no → 409.
2. `UPDATE mermas SET estado='Rechazada', motivo_rechazo=:motivo, rechazado_por=:admin, rechazado_por_nombre=:nombre, rechazado_en=now() WHERE id=:id AND estado='Registrada'`.
3. **No se toca `productos.stock`**. **No se crea `movimiento_inventario`**.

**Respuesta OK** (200): merma rechazada con detalle.

**Errores**: `403`, `404`, `409`, `422` (motivo vacío o < 5 chars).

---

## 6. Endpoints — Proveedores (CU-B12)

### 6.1 `GET /proveedores` — Listado

**Permiso**: `ADMIN`.

**Query params**: `search` (por razón social o RUC), `solo_con_deuda` (bool), `activo` (bool), `page`, `page_size`.

**Respuesta OK** (200):
```json
{
  "items": [
    {
      "id": 4,
      "razon_social": "Distribuidora Lima SAC",
      "ruc": "20123456789",
      "telefono": "+51 999 888 777",
      "email": "ventas@distlima.pe",
      "activo": true,
      "deuda_actual": 245.00
    }
  ],
  "total": 8
}
```

### 6.2 `POST /proveedores` — Alta

**Permiso**: `ADMIN`.

**Body**:
```json
{
  "razon_social": "Distribuidora Lima SAC",
  "ruc": "20123456789",
  "telefono": "+51 999 888 777",
  "email": "ventas@distlima.pe",
  "direccion": "Av. Industrial 123, Lima"
}
```

**Errores**: `409` (RUC duplicado), `422`.

### 6.3 `GET /proveedores/{id}` — Detalle

**Permiso**: `ADMIN`.

**Respuesta OK** (200): proveedor + listado de solicitudes asociadas + `deuda_actual`.

### 6.4 `PATCH /proveedores/{id}` — Edición

**Permiso**: `ADMIN`.

**Body**: cualquiera de los campos. No permite modificar `deuda_actual` directamente (solo vía compras a crédito o pagos).

### 6.5 `POST /proveedores/{id}/compras-credito` — Registrar compra al crédito

**Permiso**: `ADMIN`.

**Body**:
```json
{
  "monto": 245.00,
  "concepto": "Lote 24 Coca-Cola + 12 Galletas (Boleta 001)",
  "fecha": "2026-07-19",
  "solicitud_ingreso_id": 27
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `monto` | number | ✅ | `> 0`. |
| `concepto` | string | opcional | — |
| `fecha` | date | ✅ | Formato `YYYY-MM-DD`. |
| `solicitud_ingreso_id` | int | opcional | Si se da, FK existente. La deuda queda vinculada a esa solicitud. |

**Comportamiento** (transaccional — D-12, D-15):
1. Valida que el proveedor exista.
2. `INSERT` en `pagos_proveedor` con `tipo='compra_credito'`, `monto`, `fecha`, snapshots del admin.
3. `UPDATE proveedores SET deuda_actual = deuda_actual + :monto, updated_at = now() WHERE id = :id`.
4. `COMMIT`.

**Respuesta OK** (201):
```json
{
  "pago_proveedor_id": 88,
  "proveedor_id": 4,
  "tipo": "compra_credito",
  "monto": 245.00,
  "deuda_actual": 245.00
}
```

**Errores**: `404`, `422` (monto <= 0, FK inválida).

### 6.6 `POST /proveedores/{id}/pagos` — Registrar pago

**Permiso**: `ADMIN`.

**Body**:
```json
{
  "monto": 100.00,
  "concepto": "Pago parcial en efectivo",
  "fecha": "2026-07-19"
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `monto` | number | ✅ | `> 0` y `<= deuda_actual`. |
| `concepto` | string | opcional | — |
| `fecha` | date | ✅ | Formato `YYYY-MM-DD`. |

**Comportamiento** (transaccional — D-12):
1. `SELECT deuda_actual FOR UPDATE` (lock pesimista para evitar race conditions).
2. Valida `monto <= deuda_actual`. Si no → 422 *"El pago no puede superar la deuda actual"*.
3. `INSERT` en `pagos_proveedor` con `tipo='pago'`, `monto`, `fecha`, snapshots del admin.
4. `UPDATE proveedores SET deuda_actual = deuda_actual - :monto, updated_at = now() WHERE id = :id`.
5. `COMMIT`.

**Respuesta OK** (201):
```json
{
  "pago_proveedor_id": 89,
  "proveedor_id": 4,
  "tipo": "pago",
  "monto": 100.00,
  "deuda_actual": 145.00
}
```

**Errores**: `404`, `422` (monto > deuda, monto <= 0).

### 6.7 `GET /proveedores/{id}/pagos` — Historial de pagos (CU-B12b)

**Permiso**: `ADMIN`.

**Query params**:
| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `tipo` | string | — | Filtro: `compra_credito` o `pago`. Si se omite, ambos. |
| `fecha_desde` | date | — | — |
| `fecha_hasta` | date | — | — |
| `page` | int | 1 | — |
| `page_size` | int | 20 | max 100. |

**Respuesta OK** (200):
```json
{
  "items": [
    {
      "id": 88,
      "fecha": "2026-07-19",
      "tipo": "compra_credito",
      "monto": 245.00,
      "concepto": "Lote 24 Coca-Cola + 12 Galletas (Boleta 001)",
      "solicitud_ingreso_id": 27,
      "created_at": "2026-07-19T15:30:00-03:00",
      "registrado_por": 1,
      "registrado_por_nombre": "María (Admin)"
    },
    {
      "id": 89,
      "fecha": "2026-07-19",
      "tipo": "pago",
      "monto": 100.00,
      "concepto": "Pago parcial en efectivo",
      "solicitud_ingreso_id": null,
      "created_at": "2026-07-19T16:00:00-03:00",
      "registrado_por": 1,
      "registrado_por_nombre": "María (Admin)"
    }
  ],
  "total": 2,
  "deuda_actual": 145.00,
  "page": 1,
  "page_size": 20
}
```

**Errores**: `404`, `422`, `403`.

---

## 7. Endpoints — Inventario / Movimientos

### 7.1 `GET /inventario/movimientos` — Bitácora

**Permiso**: `ADMIN` y `CAJERO`.

**Query params**:
| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `producto_id` | int | — | Filtro por producto. |
| `tipo` | string | — | `ingreso` / `merma` / `ajuste` / `venta` / `devolucion`. |
| `fecha_desde` | date | — | — |
| `fecha_hasta` | date | — | — |
| `page` | int | 1 | — |
| `page_size` | int | 20 | max 100. |

**Respuesta OK** (200):
```json
{
  "items": [
    {
      "id": 901,
      "producto_id": 142,
      "producto_nombre": "Coca-Cola 500ml",
      "cantidad": 24,
      "tipo": "ingreso",
      "motivo": null,
      "solicitud_ingreso_id": 27,
      "merma_id": null,
      "created_at": "2026-07-19T16:00:00-03:00",
      "registrado_por": 1,
      "registrado_por_nombre": "María (Admin)"
    }
  ],
  "total": 134
}
```

**Uso**: reportes (Módulo D), auditoría, depuración.

---

## 8. Endpoints — Storage (foto de boleta, foto de producto)

> **Decisión validada 2026-07-19 (P-07)**: el backend usa **Supabase Storage** para alojar las imágenes. La URL devuelta puede ser **pública** (si el bucket es público con RLS) o **firmada con expiración** (si el bucket es privado).

### 8.1 `POST /storage/upload` — Subir archivo

**Permiso**: `ADMIN` y `CAJERO`.

**Body**: `multipart/form-data` con campo `file` (imagen JPEG/PNG, max 10 MB) y opcional `carpeta` (`boletas` | `productos`).

**Comportamiento**:
1. El backend valida el tipo MIME (`image/jpeg` o `image/png`) y el tamaño (max 10 MB).
2. Genera un nombre único: `{carpeta}/{YYYY-MM-DD}-{uuid}.{ext}`.
3. Sube el archivo a Supabase Storage vía SDK oficial (`supabase-py` o `httpx` directo al endpoint REST).
4. Si el bucket es público, devuelve la URL pública. Si es privado, devuelve una **signed URL** con expiración de 1 hora (suficiente para que el cliente la use inmediatamente y para revisar la solicitud de ingreso en la UI).
5. Persiste un registro mínimo (opcional) en la BD para auditoría: `storage_uploads` con `path`, `mime`, `size`, `subido_por`. Si se implementa, va como una tabla más en `schema_modulo_b_completo.sql`.

**Respuesta OK** (201):
```json
{
  "url": "https://<project>.supabase.co/storage/v1/object/sign/boletas/2026-07-19-uuid-001.jpg?token=...",
  "path": "boletas/2026-07-19-uuid-001.jpg",
  "filename": "2026-07-19-uuid-001.jpg",
  "mime": "image/jpeg",
  "size_bytes": 234567,
  "expires_at": "2026-07-19T17:00:00-03:00"
}
```

**Errores**: `413` (archivo muy grande), `415` (tipo no soportado), `403` (sin permiso), `502` (Supabase no responde).

### 8.2 Configuración de Supabase

- **Variables de entorno** en `backend/.env` (documentar en `docs/SCRIPTS_DEV.md` cuando se agreguen):
  - `SUPABASE_URL=https://<project>.supabase.co`
  - `SUPABASE_SERVICE_ROLE_KEY=<service-role-key>` (NO la anon key; la service role es server-side).
  - `SUPABASE_STORAGE_BUCKET_BOLETAS=boletas` (default).
  - `SUPABASE_STORAGE_BUCKET_PRODUCTOS=productos` (default).
- **Buckets**:
  - `boletas` — privado, con signed URLs. Solo accesible para ADMIN y para el solicitante de la solicitud de ingreso.
  - `productos` — público, lectura libre (las fotos se muestran en el POS y en la ficha del producto).
- **Políticas RLS** (a configurar desde el panel de Supabase):
  - `boletas`: lectura solo para usuarios autenticados del proyecto (RLS policy).
  - `productos`: lectura pública, escritura solo para service role.
- **Patrón de uso**:
  1. Cliente (POS o web admin) llama `POST /storage/upload` con el archivo.
  2. Backend sube a Supabase, devuelve URL firmada.
  3. Cliente usa esa URL en el campo `foto_boleta_url` al crear la solicitud de ingreso (`POST /ingresos`).
  4. La URL queda persistida en `solicitudes_ingreso.foto_boleta_url` y se muestra cada vez que se consulta la solicitud.

> **Importante**: si en el futuro se migra a otro servicio de storage (GCS, S3, etc.), solo cambia la implementación del adaptador. La firma del endpoint `POST /storage/upload` permanece igual.

---

## 9. Contrato con el Módulo C (Ventas)

> Esta es la **integración más importante** del módulo. **No es HTTP**: el Módulo C accede por **SQL directo** a la tabla `productos` dentro de la misma sesión de BD.

### 9.1 Por qué no HTTP

RNF-03 exige **atomicidad venta + stock**. Si el descuento de stock se hiciera por HTTP, una falla de red o timeout dejaría la venta registrada sin stock descontado (o al revés). La transacción de BD garantiza que ambos eventos pasen juntos o ninguno.

### 9.2 Tabla de `productos` que C lee y escribe

El Módulo C accede **solo** a estas columnas de `productos`:

| Columna | Tipo | Lectura | Escritura |
|---|---|---|---|
| `id` | BIGINT | ✅ | ❌ |
| `codigo` | VARCHAR(60) | ✅ | ❌ |
| `nombre` | VARCHAR(150) | ✅ (snapshot) | ❌ |
| `precio` | NUMERIC(10,2) | ✅ (snapshot) | ❌ |
| `stock` | INT | ✅ | ✅ (solo decremento) |
| `stock_minimo` | INT | ✅ (alertas) | ❌ |
| `activo` | BOOLEAN | ✅ | ❌ |
| `deleted_at` | TIMESTAMPTZ | ✅ (filtro) | ❌ |
| `updated_at` | TIMESTAMPTZ | ✅ | ✅ (en cada UPDATE) |

**Restricciones del contrato**:
- C **NO** hace `UPDATE` de columnas distintas a `stock` y `updated_at`.
- C **NO** hace `INSERT` ni `DELETE` en `productos` (responsabilidad de B vía CU-B01).
- C **NO** modifica `historial_precios` (responsabilidad de B vía CU-B10).
- B **NO** expone endpoint HTTP para descontar stock (no es necesario y crearía una API paralela al contrato SQL).

### 9.3 SQL que C ejecuta (referencia)

Implementado en `backend/app/modules/modulo_c_ventas/infrastructure/adapters/integrations/sqlalchemy_stock_adapter.py`.

**Descontar stock (en transacción de venta)**:
```sql
UPDATE productos
SET stock = stock - :cantidad,
    updated_at = now()
WHERE id = :producto_id
  AND stock >= :cantidad
  AND deleted_at IS NULL;
```

Si `rowcount = 0` → la venta debe hacer ROLLBACK.

**Reponer stock (anulación/devolución)**:
```sql
UPDATE productos
SET stock = stock + :cantidad,
    updated_at = now()
WHERE id = :producto_id;
```

**Validación pre-venta (lectura)**:
```sql
SELECT id, codigo, nombre, precio, stock, activo
FROM productos
WHERE id = ANY(:ids)
  AND deleted_at IS NULL;
```

### 9.4 Trazabilidad de movimientos de venta

**Opcional pero recomendado**: cuando C descuenta stock por una venta, debería dejar un `INSERT` en `movimientos_inventario` con `tipo='venta'`, `cantidad = -:cantidad`, `registrado_por` y nombre del cajero (snapshot). Esto **no es responsabilidad contractual** de C, pero mejora la trazabilidad del módulo B para reportes del Módulo D.

Si C no lo hace, el módulo B queda con la `movimientos_inventario` incompleta para ventas. **A coordinar con Clever** si esto debe ser obligatorio.

### 9.5 Cambios futuros que romperían el contrato

Cualquiera de estos cambios requiere coordinación previa con Clever:

- Renombrar o eliminar columnas de `productos` que C lee.
- Cambiar el tipo de `stock` (ej. de `INT` a `BIGINT`).
- Eliminar el `CHECK (stock >= 0)`.
- Eliminar el soft delete (`deleted_at`).
- Cambiar la semántica de `activo` (qué productos son visibles para el POS).

---

## 10. Contrato con el Frontend

El frontend del Módulo B ya está implementado en `frontend/src/modules/modulo-b-inventario/`. La fuente de verdad del contrato son los `*.port.ts`:

| Archivo | Define el contrato de |
|---|---|
| `services/productos.port.ts` | `GET /productos`, `GET /productos/{id}`, `GET /productos/buscar`, `POST /productos`, `PATCH /productos/{id}`, `PATCH /productos/{id}/precio`, `GET /productos/{id}/historial-precios`, `GET /productos/por-reponer`. |
| `services/categorias.port.ts` | `GET /categorias`, `POST /categorias`, `PATCH /categorias/{id}`. |
| `services/ingresos.port.ts` | `GET /ingresos`, `GET /ingresos/{id}`, `POST /ingresos`, `POST /ingresos/{id}/aprobar`, `POST /ingresos/{id}/rechazar`. |
| `services/mermas.port.ts` | `GET /mermas`, `GET /mermas/{id}`, `POST /mermas`. |
| `services/proveedores.port.ts` | `GET /proveedores`, `GET /proveedores/{id}`, `POST /proveedores`, `PATCH /proveedores/{id}`, `POST /proveedores/{id}/pagos`. |

**Regla del proyecto** (de `docs/FRONTEND_DISENO.md:107-108`): si el backend respeta la forma de los `*.port.ts`, el frontend funciona sin tocar una línea de React. Los tipos en `types/index.ts` deben coincidir 1 a 1 con los Pydantic schemas del backend.

### 10.1 Mobile-first (HU-B09, RNF-12)

La pantalla **Inventario** (`pages/Inventario.tsx`) debe:

- Renderizar lista de productos como **tarjetas**, no tablas, en viewports < 768 px.
- Sticky search bar arriba.
- Filtros en bottom-sheet o modal.
- Imágenes de producto con `loading="lazy"`.
- Paginación infinita al hacer scroll (no botones de paginación en mobile).
- Botón flotante (FAB) para escanear código de barras (`@zxing/library` o similar).

### 10.2 Flujo de aprobación mobile (HU-B07)

La pantalla **Aprobación de Ingresos** (`pages/AprobacionIngresos.tsx`) debe:

- Mostrar la cola de pendientes con foto de boleta visible.
- Botón **Aprobar** (verde) y **Rechazar** (rojo) grandes, accesibles con pulgar.
- Al rechazar, abrir un modal con textarea para `motivo_rechazo` (mínimo 5 chars, validado en cliente y servidor).
- Confirmación antes de ejecutar la acción.

---

## 11. Códigos de error

| Código | Significado | Cuándo |
|---|---|---|
| `400` | Bad Request | Body malformado. |
| `401` | Unauthorized | JWT ausente, inválido o expirado. |
| `403` | Forbidden | Rol insuficiente. (Cajero intentando aprobar, cambiar precio, etc.) |
| `404` | Not Found | Recurso inexistente o borrado lógicamente. |
| `409` | Conflict | UNIQUE (código duplicado, RUC duplicado), operación no permitida por estado (solicitud ya aprobada), stock insuficiente en merma o venta. |
| `413` | Payload Too Large | Archivo > 10 MB. |
| `415` | Unsupported Media Type | Tipo de archivo no permitido. |
| `422` | Unprocessable Entity | Validación de campos (precio negativo, cantidad cero, motivo muy corto). |
| `423` | Locked | Cuenta de usuario bloqueada (heredado de A). |
| `500` | Internal Server Error | Error inesperado. Loggear con `request_id`. |

**Formato de error** (consistente con el resto del proyecto):
```json
{ "detail": "Ya existe un producto con ese código" }
```

---

## 12. Decisiones validadas con el equipo (2026-07-19)

Todas las decisiones de diseño abiertas al inicio de esta documentación fueron resueltas en la sesión del 2026-07-19. Aplica la **regla del proyecto**: la documentación del repositorio es la fuente de verdad (ver `conventions/repo-over-prompt` en Engram).

| # | Punto | Resolución | Impacto en la API |
|---|---|---|---|
| P-01 | Texto oficial de RNF-02 | No documentado en el repo; se mantiene interpretación tentativa (≤1s). | Cuando aparezca el texto oficial, ajustar `/productos/buscar` (cache, ETag). |
| P-02 | Texto oficial de RNF-06 | No documentado; interpretación tentativa. | Cuando aparezca, documentar estrategia de backup + restore. |
| P-03 | Texto oficial de RNF-09 | No documentado; interpretación tentativa. | PostgreSQL ya lo cubre en RDS/Cloud SQL. |
| P-05 | Cajero puede registrar mermas | **Sí**, con validación posterior. | `POST /mermas` ahora permite `CAJERO`. Agregados `POST /mermas/{id}/confirmar` y `POST /mermas/{id}/rechazar` (solo ADMIN). |
| P-06 | Tabla `pagos_proveedor` desde el día 1 | **Sí**, se crea. | `POST /proveedores/{id}/compras-credito` y `POST /proveedores/{id}/pagos` ahora también insertan en `pagos_proveedor`. Agregado `GET /proveedores/{id}/pagos` (historial). |
| P-07 | Storage de fotos | **Supabase Storage**. | `POST /storage/upload` implementado con el SDK de Supabase. Buckets separados para `boletas` (privado, signed URL) y `productos` (público). |
| P-08 | Trazabilidad de ventas en `movimientos_inventario` | Pendiente de coordinar con Clever. | Si C debe hacer INSERT de `tipo='venta'`, se documenta en el contrato entre módulos. No bloquea esta doc. |

---

## 13. Resumen ejecutivo

- **20 endpoints HTTP** propios, agrupados en 7 recursos: productos, categorías, ingresos, mermas, proveedores, movimientos, storage.
- **0 endpoints HTTP para el Módulo C**: el contrato con C es **SQL directo** a `productos` (RNF-03).
- **Permisos validados en backend** (no solo UI):
  - `CAJERO` puede: leer productos/categorías/ingresos, crear solicitudes de ingreso, **reportar mermas** (paso 1), consultar inventario.
  - `CAJERO` NO puede: aprobar/rechazar ingresos, confirmar/rechazar mermas, cambiar precios, gestionar proveedores, registrar compras a crédito ni pagos.
  - `ADMIN` puede todo lo anterior más la validación de mermas y la gestión de proveedores.
- **El contrato con el frontend ya está implementado** en los `*.port.ts`. La responsabilidad de este módulo es respetarlo. **Nota**: si en el frontend faltan los `*.port.ts` para `mermas/{id}/confirmar`, `mermas/{id}/rechazar` y `proveedores/{id}/pagos` (GET), se crean cuando se implementen las pantallas correspondientes.
- **Atomicidad de stock** garantizada con `CHECK (stock >= 0)` + transacciones + filtro `WHERE stock >= :cantidad` en UPDATE.
- **Atomicidad de deuda** garantizada con `SELECT ... FOR UPDATE` + INSERT en `pagos_proveedor` + UPDATE en `proveedores.deuda_actual`, todo en la misma transacción.
- **7 decisiones validadas** con el equipo el 2026-07-19 (ver sección 12 y ER_MODULO_B.md sección 7).
