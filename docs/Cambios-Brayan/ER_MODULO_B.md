# Módulo B — Catálogo, Inventario y Aprobación de Ingresos

> Documento de **diseño de datos** del Módulo B.
> Autor: Brayan. Mantenedor: equipo Módulo B.
> Versión: 1.0 (alineada con el estado actual del repo a la fecha de este commit).

## 1. Alcance

Este documento define el **modelo entidad–relación completo** del Módulo B del sistema K.I.O.S.K.O, incluyendo:

- El **diagrama ER** (Mermaid) con las entidades a cargo del módulo.
- La **descripción tabular** de cada entidad (columnas, tipos, PK/FK/UK, restricciones).
- Las **decisiones de diseño** (soft delete, snapshot del nombre, idempotencia, etc.).
- El **script DDL** (PostgreSQL 16) necesario para crear las tablas que **aún no existen** en el repo.

### 1.1 Requisitos funcionales cubiertos

`RF-03`, `RF-04`, `RF-05`, `RF-06`, `RF-08`, `RF-09`, `RF-18`, `RF-23`, `RF-24`, `RF-27`.

### 1.2 Requisitos no funcionales asociados

`RNF-02`, `RNF-03`, `RNF-06`, `RNF-09`, `RNF-12`.

> ⚠️ **PENDIENTE DE CONFIRMACIÓN CON EL EQUIPO**: los textos oficiales de `RNF-02`, `RNF-06` y `RNF-09` **no se encuentran documentados** en el repositorio (búsqueda exhaustiva en `docs/`). Solo `RNF-03` (atomicidad venta + stock) y `RNF-12` (supervisión de movimientos del turno) aparecen referenciados, y de forma parcial. La sección 7 de este documento lista las interpretaciones adoptadas hasta que el equipo confirme o ajuste el texto. **No se debe tomar como definición formal**; cualquier corrección posterior puede requerir ajustes en este ER.

### 1.3 Historias de usuario cubiertas

Las **14 historias de usuario** del Módulo B (`HU-B01` … `HU-B14`) se mapean a este modelo y se detallan en `CASOS_DE_USO_MODULO_B.md` y `API_MODULO_B.md`.

---

## 2. Estado de las tablas en el repositorio

Antes de diseñar, es importante distinguir lo que **ya está creado** en el repo de lo que **falta**:

| Tabla | Estado | Ubicación | Observación |
|---|---|---|---|
| `categorias` | ✅ **Existe** (mínima) | `backend/db/schema_modulo_b_minimo.sql:10-13` | Creada temporalmente por Clever para habilitar el POS del Módulo C. **No se redefine**, se documenta acá. |
| `productos` | ✅ **Existe** (mínima) | `backend/db/schema_modulo_b_minimo.sql:15-31` | Creada temporalmente por Clever. **Crítico**: el Módulo C la lee por SQL directo (RNF-03), por lo que **no se puede alterar su estructura** sin coordinar con C. |
| `movimientos_inventario` | ❌ **Falta** | — | Diseño nuevo (sección 4.3). |
| `solicitudes_ingreso` | ❌ **Falta** | — | Diseño nuevo (sección 4.4). |
| `detalle_solicitud` | ❌ **Falta** | — | Diseño nuevo (sección 4.5). |
| `proveedores` | ❌ **Falta** | — | Diseño nuevo (sección 4.6). |
| `pagos_proveedor` | ❌ **Falta** | — | Diseño nuevo (sección 4.7). **Decisión validada con el equipo el 2026-07-19**: la trazabilidad de pagos/compras a crédito se persiste desde el día 1, no se hace denormalizado. |
| `mermas` | ❌ **Falta** | — | Diseño nuevo (sección 4.8). **Decisión validada con el equipo el 2026-07-19**: el cajero puede registrar mermas, con estado `Registrada`; un ADMIN debe confirmarlas o rechazarlas. |
| `historial_precios` | ❌ **Falta** | — | Diseño nuevo (sección 4.9). |

> **Nota importante sobre "stock"**: el prompt del módulo lista una tabla `stock` separada. En el repositorio **no existe ni debería existir**: el stock es la columna `productos.stock` (con `CHECK stock >= 0`). El historial de cambios se materializa en `movimientos_inventario`. Esta es la decisión de diseño **D-01** (ver sección 5).

---

## 3. Diagrama Entidad–Relación

```mermaid
erDiagram
    USUARIOS_A ||--o{ PRODUCTOS              : "creado_por"
    USUARIOS_A ||--o{ PRODUCTOS              : "actualizado_por"
    USUARIOS_A ||--o{ SOLICITUDES_INGRESO    : "solicitado_por"
    USUARIOS_A ||--o{ SOLICITUDES_INGRESO    : "revisado_por"
    USUARIOS_A ||--o{ MOVIMIENTOS_INVENTARIO : "registrado_por"
    USUARIOS_A ||--o{ MERMAS                 : "registrado_por"
    USUARIOS_A ||--o{ HISTORIAL_PRECIOS      : "modificado_por"
    USUARIOS_A ||--o{ PROVEEDORES            : "creado_por"

    CATEGORIAS ||--o{ PRODUCTOS              : "agrupa"
    PRODUCTOS  ||--o{ DETALLE_SOLICITUD      : "incluye"
    PRODUCTOS  ||--o{ MOVIMIENTOS_INVENTARIO : "afecta"
    PRODUCTOS  ||--o{ HISTORIAL_PRECIOS      : "cambia_precio"
    PRODUCTOS  ||--o{ MERMAS                 : "descuenta"
    PROVEEDORES ||--o{ SOLICITUDES_INGRESO   : "provee"
    PROVEEDORES ||--o{ MERMAS                : "asociado_a"
    PROVEEDORES ||--o{ PAGOS_PROVEEDOR       : "registra_pagos"
    SOLICITUDES_INGRESO ||--|{ DETALLE_SOLICITUD : "compuesta_por"
    SOLICITUDES_INGRESO ||--o{ MOVIMIENTOS_INVENTARIO : "genera"
    MERMAS ||--o|{ MOVIMIENTOS_INVENTARIO   : "al_confirmarse_genera"

    PRODUCTOS {
        BIGSERIAL id PK
        VARCHAR_60 codigo UK "barras o interno; único"
        VARCHAR_150 nombre
        INT categoria_id FK
        NUMERIC_10_2 precio_venta
        NUMERIC_10_2 precio_compra_actual
        INT stock "CHECK stock >= 0"
        INT stock_minimo
        BOOLEAN activo
        BOOLEAN es_codigo_interno "TRUE si no tiene código de barras"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ deleted_at "soft delete"
        BIGINT deleted_by
        BIGINT creado_por FK "snapshot a usuarios"
        VARCHAR_100 creado_por_nombre "snapshot"
        BIGINT actualizado_por FK
        VARCHAR_100 actualizado_por_nombre "snapshot"
    }

    CATEGORIAS {
        SERIAL id PK
        VARCHAR_80 nombre UK
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ deleted_at
        BIGINT deleted_by
    }

    MOVIMIENTOS_INVENTARIO {
        BIGSERIAL id PK
        BIGINT producto_id FK
        INT cantidad "positiva=entrada, negativa=salida"
        VARCHAR_20 tipo "ingreso|merma|ajuste|venta|devolucion"
        VARCHAR_200 motivo "obligatorio si tipo=merma"
        BIGINT solicitud_ingreso_id FK "nullable; no nulo si tipo=ingreso"
        BIGINT merma_id FK "nullable; no nulo si tipo=merma"
        TIMESTAMPTZ created_at
        BIGINT registrado_por FK
        VARCHAR_100 registrado_por_nombre "snapshot"
    }

    SOLICITUDES_INGRESO {
        BIGSERIAL id PK
        BIGINT proveedor_id FK "nullable para ingresos sin proveedor"
        VARCHAR_20 estado "Pendiente|Aprobada|Rechazada"
        TEXT foto_boleta_url "obligatoria al enviar"
        TEXT motivo_rechazo "nulo si aprobada o pendiente"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ deleted_at
        BIGINT deleted_by
        BIGINT solicitado_por FK
        VARCHAR_100 solicitado_por_nombre "snapshot"
        BIGINT revisado_por FK "nullable hasta que se revise"
        VARCHAR_100 revisado_por_nombre "snapshot"
        TIMESTAMPTZ revisado_en "nullable"
    }

    DETALLE_SOLICITUD {
        BIGSERIAL id PK
        BIGINT solicitud_id FK
        BIGINT producto_id FK
        INT cantidad
        NUMERIC_10_2 precio_compra_unitario "registrado al solicitar"
        TIMESTAMPTZ created_at
    }

    PROVEEDORES {
        BIGSERIAL id PK
        VARCHAR_120 razon_social
        VARCHAR_20 ruc "nullable; único si no es nulo"
        VARCHAR_20 telefono
        VARCHAR_120 email
        TEXT direccion
        BOOLEAN activo
        NUMERIC_12_2 deuda_actual "monto pendiente de pago al crédito"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        TIMESTAMPTZ deleted_at
        BIGINT deleted_by
        BIGINT creado_por FK
        VARCHAR_100 creado_por_nombre "snapshot"
    }

    MERMAS {
        BIGSERIAL id PK
        BIGINT producto_id FK
        INT cantidad
        VARCHAR_30 motivo "vencimiento|rotura|otro"
        TEXT observacion
        BIGINT proveedor_id FK "nullable; si la merma es de mercadería recibida de un proveedor"
        VARCHAR_20 estado "Registrada|Confirmada|Rechazada; default Registrada"
        TEXT motivo_rechazo "obligatorio si estado=Rechazada"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ deleted_at "soft delete"
        BIGINT deleted_by
        BIGINT registrado_por FK "snapshot a usuarios"
        VARCHAR_100 registrado_por_nombre "snapshot"
        BIGINT confirmado_por FK "nullable; solo si estado=Confirmada"
        VARCHAR_100 confirmado_por_nombre "snapshot"
        TIMESTAMPTZ confirmado_en "nullable"
        BIGINT rechazado_por FK "nullable; solo si estado=Rechazada"
        VARCHAR_100 rechazado_por_nombre "snapshot"
        TIMESTAMPTZ rechazado_en "nullable"
    }

    PAGOS_PROVEEDOR {
        BIGSERIAL id PK
        BIGINT proveedor_id FK
        VARCHAR_20 tipo "compra_credito|pago"
        NUMERIC_12_2 monto "positivo siempre"
        TEXT concepto
        DATE fecha
        BIGINT solicitud_ingreso_id FK "nullable; cuando tipo=compra_credito originada en un ingreso"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ deleted_at "soft delete"
        BIGINT deleted_by
        BIGINT registrado_por FK
        VARCHAR_100 registrado_por_nombre "snapshot"
    }

    HISTORIAL_PRECIOS {
        BIGSERIAL id PK
        BIGINT producto_id FK
        NUMERIC_10_2 precio_anterior "nulo si es el alta"
        NUMERIC_10_2 precio_nuevo
        VARCHAR_20 tipo_precio "venta|compra"
        TIMESTAMPTZ created_at "inmutable; nunca UPDATE"
        BIGINT modificado_por FK
        VARCHAR_100 modificado_por_nombre "snapshot"
    }
```

> **Leyenda del diagrama**: las relaciones hacia `USUARIOS_A` son **claves foráneas lógicas** al Módulo A; en SQL se nombran como `*_id` con `ON DELETE RESTRICT` (no se redefine la tabla `usuarios` acá, solo se referencia). Ver sección 6.

---

## 4. Descripción de entidades

### 4.1 `productos` (existente, NO modificar)

Definida en `backend/db/schema_modulo_b_minimo.sql:15-31`. Se documenta acá para tener la foto completa.

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | Identificador interno. |
| `codigo` | `VARCHAR(60)` | **UNIQUE**, `NOT NULL` | Código de barras (EAN-13/128) o código interno (`PAP-001`). Único global, sin importar el tipo. |
| `nombre` | `VARCHAR(150)` | `NOT NULL` | Nombre para mostrar en catálogos y tickets. |
| `categoria_id` | `INT` | **FK → `categorias(id)`** `ON DELETE RESTRICT` | Categoría. |
| `precio` | `NUMERIC(10,2)` | `NOT NULL`, `CHECK (precio >= 0)` | Precio de venta actual. Se conserva historial en `historial_precios`. |
| `stock` | `INT` | `NOT NULL DEFAULT 0`, `CHECK (stock >= 0)` | Stock actual. **Es la fuente de verdad para ventas**. |
| `stock_minimo` | `INT` | `NOT NULL DEFAULT 0`, `CHECK (stock_minimo >= 0)` | Umbral de alerta (HU-B13). |
| `activo` | `BOOLEAN` | `NOT NULL DEFAULT TRUE` | Si está disponible para venta. El POS no muestra inactivos. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `deleted_at` | `TIMESTAMPTZ` | `NULL` por defecto | Soft delete. Filtrar siempre `WHERE deleted_at IS NULL`. |
| `deleted_by` | `BIGINT` | `NULL` por defecto | Quién borró (referencia lógica a `usuarios.id`). |

**Índices**: PK en `id`; UNIQUE en `codigo`; FK indexada implícita en `categoria_id`. **Pendiente**: agregar `INDEX idx_productos_nombre` (búsqueda por nombre, HU-B04) y `INDEX idx_productos_activo_stock` (alertas de stock mínimo, HU-B13).

> **No se redefine la DDL** porque la tabla ya existe y el Módulo C la lee por SQL directo. Las **extensiones** (columnas adicionales como `es_codigo_interno`, `precio_compra_actual`, snapshots) se agregan en una **migración aditiva** con `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (ver sección 8).

### 4.2 `categorias` (existente, NO modificar)

Definida en `backend/db/schema_modulo_b_minimo.sql:10-13`.

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `SERIAL` | **PK** | — |
| `nombre` | `VARCHAR(80)` | **UNIQUE**, `NOT NULL` | Nombre de la categoría. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `deleted_at` | `TIMESTAMPTZ` | `NULL` por defecto | Soft delete. |

**Índices**: PK en `id`; UNIQUE en `nombre`. **Sin FKs salientes** (es tabla raíz del catálogo).

### 4.3 `movimientos_inventario` (nueva)

Bitácora de **toda** variación de stock. Es **append-only** (solo `INSERT`, nunca `UPDATE`/`DELETE`).

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | — |
| `producto_id` | `BIGINT` | **FK → `productos(id)`** `ON DELETE RESTRICT` | Producto afectado. |
| `cantidad` | `INT` | `NOT NULL`, `CHECK (cantidad <> 0)` | **Positiva = entrada**, **negativa = salida**. |
| `tipo` | `VARCHAR(20)` | `NOT NULL`, `CHECK (tipo IN ('ingreso','merma','ajuste','venta','devolucion'))` | Categoría del movimiento. |
| `motivo` | `VARCHAR(200)` | `NULL` salvo si `tipo='merma'` | Justificación cuando aplica. |
| `solicitud_ingreso_id` | `BIGINT` | **FK → `solicitudes_ingreso(id)`** `ON DELETE RESTRICT`, `NULL` | Solo si `tipo='ingreso'`. |
| `merma_id` | `BIGINT` | **FK → `mermas(id)`** `ON DELETE RESTRICT`, `NULL` | Solo si `tipo='merma'`. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Cuándo se registró el movimiento. |
| `registrado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT` | Quién lo hizo. |
| `registrado_por_nombre` | `VARCHAR(100)` | `NOT NULL` | Snapshot del nombre. |

**Índices**:
- `idx_mov_producto_fecha (producto_id, created_at DESC)` — reportes y trazabilidad por producto.
- `idx_mov_tipo (tipo)` — filtros por tipo.
- `idx_mov_solicitud (solicitud_ingreso_id)` — para reconstruir el impacto de una solicitud.

**Restricciones cruzadas (CHECK)**:
- Si `tipo='ingreso'` → `solicitud_ingreso_id IS NOT NULL`.
- Si `tipo='merma'` → `merma_id IS NOT NULL` y `motivo IS NOT NULL`.
- `cantidad > 0` si `tipo IN ('ingreso','devolucion')`.
- `cantidad < 0` si `tipo IN ('merma','venta')`.
- `cantidad` puede ser cualquier signo si `tipo='ajuste'`.

### 4.4 `solicitudes_ingreso` (nueva)

Cabecera del flujo de **aprobación de ingresos** (HU-B06, HU-B07, HU-B08). El stock **no se toca** hasta que el estado pasa a `Aprobada`.

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | — |
| `proveedor_id` | `BIGINT` | **FK → `proveedores(id)`** `ON DELETE RESTRICT`, `NULL` | Proveedor. Puede ser `NULL` para ingresos informales. |
| `estado` | `VARCHAR(20)` | `NOT NULL`, `CHECK (estado IN ('Pendiente','Aprobada','Rechazada'))`, `DEFAULT 'Pendiente'` | Estado del flujo. |
| `foto_boleta_url` | `TEXT` | `NOT NULL` | URL de la foto de la boleta/factura (S3/Supabase Storage). **Sin foto no se puede enviar la solicitud** (HU-B06). |
| `motivo_rechazo` | `TEXT` | `NULL` salvo si `estado='Rechazada'` | Justificación del rechazo. |
| `solicitado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT` | Quién creó la solicitud. |
| `solicitado_por_nombre` | `VARCHAR(100)` | `NOT NULL` | Snapshot. |
| `revisado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT`, `NULL` | Quién aprobó/rechazó. |
| `revisado_por_nombre` | `VARCHAR(100)` | `NULL` hasta que se revise | Snapshot. |
| `revisado_en` | `TIMESTAMPTZ` | `NULL` hasta que se revise | Cuándo se resolvió. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `deleted_at` | `TIMESTAMPTZ` | `NULL` por defecto | Soft delete. |
| `deleted_by` | `BIGINT` | `NULL` por defecto | — |

**Índices**:
- `idx_solic_estado (estado, created_at DESC)` — vista principal del cajero y la administradora.
- `idx_solic_solicitante (solicitado_por, created_at DESC)` — "mis solicitudes" del cajero.
- `idx_solic_proveedor (proveedor_id)` — reportes por proveedor.

**Reglas de transición de estado** (aplicadas en backend, validadas con CHECK + lógica de use case):
- `Pendiente → Aprobada`: solo rol `ADMIN`. Genera `movimientos_inventario` por cada línea y actualiza `productos.stock` dentro de **una transacción**.
- `Pendiente → Rechazada`: solo rol `ADMIN`. Exige `motivo_rechazo` no vacío. No toca stock.
- Cualquier otro cambio de estado está prohibido.

### 4.5 `detalle_solicitud` (nueva)

Líneas de cada solicitud de ingreso (relación 1 a muchos con la cabecera).

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | — |
| `solicitud_id` | `BIGINT` | **FK → `solicitudes_ingreso(id)`** `ON DELETE CASCADE` | Cabecera. `CASCADE` porque la línea no tiene sentido sin la solicitud. |
| `producto_id` | `BIGINT` | **FK → `productos(id)`** `ON DELETE RESTRICT` | Producto a ingresar. |
| `cantidad` | `INT` | `NOT NULL`, `CHECK (cantidad > 0)` | Cantidad a ingresar. |
| `precio_compra_unitario` | `NUMERIC(10,2)` | `NOT NULL`, `CHECK (precio_compra_unitario >= 0)` | Precio de compra al momento de la solicitud. Se **congela** acá: aunque luego cambie `productos.precio_compra_actual`, esta línea preserva el valor original. |

**Índices**:
- `idx_detsol_solicitud (solicitud_id)`.
- `idx_detsol_producto (producto_id)` — para reconstruir historial de compras.

### 4.6 `proveedores` (nueva)

Maestro de proveedores con **control de deuda** por compras al crédito (HU-B14).

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | — |
| `razon_social` | `VARCHAR(120)` | `NOT NULL` | Nombre del proveedor. |
| `ruc` | `VARCHAR(20)` | **UNIQUE** (cuando no es NULL) | RUC / DNI. `NULL` permitido para proveedores informales. |
| `telefono` | `VARCHAR(20)` | `NULL` | — |
| `email` | `VARCHAR(120)` | `NULL` | — |
| `direccion` | `TEXT` | `NULL` | — |
| `activo` | `BOOLEAN` | `NOT NULL DEFAULT TRUE` | Si se puede operar con él. |
| `deuda_actual` | `NUMERIC(12,2)` | `NOT NULL DEFAULT 0`, `CHECK (deuda_actual >= 0)` | Monto pendiente de pago al crédito. Se actualiza con cada compra al crédito y con cada pago. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | — |
| `deleted_at` | `TIMESTAMPTZ` | `NULL` por defecto | Soft delete. |
| `deleted_by` | `BIGINT` | `NULL` por defecto | — |
| `creado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT` | — |
| `creado_por_nombre` | `VARCHAR(100)` | `NOT NULL` | Snapshot. |

**Índices**:
- PK en `id`; UNIQUE en `ruc` (parcial, `WHERE ruc IS NOT NULL`).
- `idx_proveedores_razon (LOWER(razon_social))` — búsqueda case-insensitive.

> **Nota sobre `deuda_actual`**: el campo se mantiene como **denormalizado controlado** para vistas rápidas (HU-B14). El historial completo de movimientos de deuda (compras a crédito y pagos) está en la tabla `pagos_proveedor` (sección 4.7). Toda escritura en `deuda_actual` debe ir **dentro de la misma transacción** que inserta la fila correspondiente en `pagos_proveedor`. Para validar consistencia: `deuda_actual = SUM(monto WHERE tipo='compra_credito') - SUM(monto WHERE tipo='pago')` (excluyendo soft-deleted).

### 4.7 `pagos_proveedor` (nueva)

Historial de **todos los movimientos de deuda** con un proveedor: tanto compras a crédito (que **aumentan** la deuda) como pagos (que la **disminuyen**). Decisión validada con el equipo el 2026-07-19: la trazabilidad se persiste desde el día 1, no como denormalizado.

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | — |
| `proveedor_id` | `BIGINT` | **FK → `proveedores(id)`** `ON DELETE RESTRICT` | Proveedor afectado. |
| `tipo` | `VARCHAR(20)` | `NOT NULL`, `CHECK (tipo IN ('compra_credito','pago'))` | Si fue una compra que aumenta deuda (`compra_credito`) o un pago que la disminuye (`pago`). |
| `monto` | `NUMERIC(12,2)` | `NOT NULL`, `CHECK (monto > 0)` | Monto del movimiento. **Siempre positivo**; el signo lo define `tipo`. |
| `concepto` | `TEXT` | `NULL` | Nota libre. |
| `fecha` | `DATE` | `NOT NULL` | Fecha del movimiento (puede ser pasada; ej. pago retroactivo). |
| `solicitud_ingreso_id` | `BIGINT` | **FK → `solicitudes_ingreso(id)`** `ON DELETE RESTRICT`, `NULL` | Si el movimiento se originó en una solicitud de ingreso aprobada, se vincula. Solo aplica a `tipo='compra_credito'`. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Cuándo se registró. |
| `deleted_at` | `TIMESTAMPTZ` | `NULL` por defecto | Soft delete. |
| `deleted_by` | `BIGINT` | `NULL` por defecto | — |
| `registrado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT` | Quién lo registró. |
| `registrado_por_nombre` | `VARCHAR(100)` | `NOT NULL` | Snapshot. |

**Índices**:
- `idx_pagos_proveedor (proveedor_id, fecha DESC)` — historial por proveedor.
- `idx_pagos_tipo (tipo)` — filtros por tipo de movimiento.
- `idx_pagos_solicitud (solicitud_ingreso_id) WHERE solicitud_ingreso_id IS NOT NULL` — para reconstruir la deuda de una solicitud específica.

**Restricciones cruzadas (CHECK)**:
- `solicitud_ingreso_id IS NOT NULL` solo si `tipo='compra_credito'`.

**Consistencia con `proveedores.deuda_actual`** (validación a nivel de aplicación, no en SQL):
```
deuda_actual = SUM(monto WHERE tipo='compra_credito' AND deleted_at IS NULL)
             - SUM(monto WHERE tipo='pago' AND deleted_at IS NULL)
```
Esta fórmula **debe** cumplirse en todo momento. Las escrituras en `deuda_actual` y en `pagos_proveedor` van en la **misma transacción**.

### 4.8 `mermas` (nueva)

Registro de **pérdidas** (vencimientos, roturas, otros). Diferenciadas explícitamente de ventas y de "robos" (HU-B12, regla de negocio transversal).

**Flujo de dos pasos** (decisión validada con el equipo el 2026-07-19):
- **Paso 1 — Registro**: cualquier usuario (`ADMIN` o `CAJERO`) crea la merma con `estado='Registrada'`. **No** toca `productos.stock`, **no** crea `movimiento_inventario`.
- **Paso 2 — Confirmación o rechazo**: solo `ADMIN`. Si confirma → `estado='Confirmada'`, descuenta stock, crea `movimiento_inventario`. Si rechaza → `estado='Rechazada'`, exige `motivo_rechazo`, no toca stock.

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | — |
| `producto_id` | `BIGINT` | **FK → `productos(id)`** `ON DELETE RESTRICT` | Producto perdido. |
| `cantidad` | `INT` | `NOT NULL`, `CHECK (cantidad > 0)` | Unidades perdidas. |
| `motivo` | `VARCHAR(30)` | `NOT NULL`, `CHECK (motivo IN ('vencimiento','rotura','otro'))` | Categoría de la pérdida. |
| `observacion` | `TEXT` | `NULL` | Nota libre. |
| `proveedor_id` | `BIGINT` | **FK → `proveedores(id)`** `ON DELETE RESTRICT`, `NULL` | Si la mercadería provenía de un proveedor específico. |
| `estado` | `VARCHAR(20)` | `NOT NULL DEFAULT 'Registrada'`, `CHECK (estado IN ('Registrada','Confirmada','Rechazada'))` | Estado del flujo de validación. |
| `motivo_rechazo` | `TEXT` | `NULL` salvo si `estado='Rechazada'` | Justificación del rechazo. |
| `registrado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT` | Quién la registró (paso 1). |
| `registrado_por_nombre` | `VARCHAR(100)` | `NOT NULL` | Snapshot. |
| `confirmado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT`, `NULL` | ADMIN que confirmó. |
| `confirmado_por_nombre` | `VARCHAR(100)` | `NULL` salvo si `estado='Confirmada'` | Snapshot. |
| `confirmado_en` | `TIMESTAMPTZ` | `NULL` salvo si `estado='Confirmada'` | Cuándo se confirmó. |
| `rechazado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT`, `NULL` | ADMIN que rechazó. |
| `rechazado_por_nombre` | `VARCHAR(100)` | `NULL` salvo si `estado='Rechazada'` | Snapshot. |
| `rechazado_en` | `TIMESTAMPTZ` | `NULL` salvo si `estado='Rechazada'` | Cuándo se rechazó. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Cuándo se registró. |
| `deleted_at` | `TIMESTAMPTZ` | `NULL` por defecto | Soft delete. |
| `deleted_by` | `BIGINT` | `NULL` por defecto | — |

**Índices**:
- `idx_mermas_producto_fecha (producto_id, created_at DESC) WHERE deleted_at IS NULL`.
- `idx_mermas_motivo (motivo) WHERE deleted_at IS NULL` — reportes por tipo de pérdida.
- `idx_mermas_estado (estado, created_at DESC) WHERE deleted_at IS NULL` — vista de admin para pendientes de validación.

**Restricciones cruzadas (CHECK)**:
- Si `estado='Registrada'` → `confirmado_por IS NULL` y `rechazado_por IS NULL`.
- Si `estado='Confirmada'` → `confirmado_por IS NOT NULL`, `confirmado_en IS NOT NULL`, `motivo_rechazo IS NULL`.
- Si `estado='Rechazada'` → `rechazado_por IS NOT NULL`, `rechazado_en IS NOT NULL`, `motivo_rechazo IS NOT NULL` y `length(trim(motivo_rechazo)) >= 5`.

**Comportamiento transaccional**:
- **Al registrar (paso 1)**: solo `INSERT` en `mermas` con `estado='Registrada'`. **Stock intacto**. **No** crea `movimiento_inventario`.
- **Al confirmar (paso 2)**: dentro de una sola transacción: a) `SELECT ... FOR UPDATE` verifica `estado='Registrada'`. b) `UPDATE mermas SET estado='Confirmada', confirmado_por=:admin, confirmado_por_nombre=:nombre, confirmado_en=now() WHERE id=:id AND estado='Registrada'`. c) `INSERT` en `movimientos_inventario` con `tipo='merma'`, `cantidad = -mermas.cantidad`, `merma_id = mermas.id`, `motivo` justificado. d) `UPDATE productos SET stock = stock - :cantidad, updated_at = now() WHERE id = :producto_id AND stock >= :cantidad AND deleted_at IS NULL`. Si `rowcount = 0` → ROLLBACK → 409 *"Stock insuficiente"*. e) `COMMIT`.
- **Al rechazar (paso 2)**: dentro de una sola transacción: `UPDATE mermas SET estado='Rechazada', motivo_rechazo=:motivo, rechazado_por=:admin, rechazado_por_nombre=:nombre, rechazado_en=now() WHERE id=:id AND estado='Registrada'`. **Stock intacto**. **No** crea `movimiento_inventario`.

### 4.9 `historial_precios` (nueva)

Bitácora **inmutable** de cambios de precio (HU-B11). Nunca `UPDATE`, solo `INSERT`.

| Columna | Tipo SQL | Restricción | Descripción |
|---|---|---|---|
| `id` | `BIGSERIAL` | **PK** | — |
| `producto_id` | `BIGINT` | **FK → `productos(id)`** `ON DELETE RESTRICT` | Producto cuyo precio cambió. |
| `precio_anterior` | `NUMERIC(10,2)` | `NULL` solo en el alta inicial | Precio previo. `NULL` = primer registro. |
| `precio_nuevo` | `NUMERIC(10,2)` | `NOT NULL`, `CHECK (precio_nuevo >= 0)` | Precio nuevo. |
| `tipo_precio` | `VARCHAR(20)` | `NOT NULL`, `CHECK (tipo_precio IN ('venta','compra'))` | Si fue cambio de precio de venta o de compra. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Cuándo se cambió. **Nunca se modifica.** |
| `modificado_por` | `BIGINT` | **FK → `usuarios(id)`** `ON DELETE RESTRICT` | Quién lo cambió. |
| `modificado_por_nombre` | `VARCHAR(100)` | `NOT NULL` | Snapshot. |

**Índices**:
- `idx_historial_producto_fecha (producto_id, tipo_precio, created_at DESC)` — consultas de histórico por producto y tipo.

**Trigger opcional** (documentado, no se instala acá): `BEFORE UPDATE` que lanza `RAISE EXCEPTION` para reforzar la inmutabilidad a nivel de BD. Es una segunda línea de defensa; la principal es la convención del código.

---

## 5. Decisiones de diseño

### D-01 — Stock como columna de `productos`, no como tabla separada
El prompt original menciona una tabla `stock`. En el repositorio **ya está implementado** como `productos.stock` (`CHECK stock >= 0`). Mantenerlo así:
- Permite que el Módulo C descuente stock por SQL directo en la **misma transacción** que registra la venta (RNF-03).
- La bitácora histórica de cambios está en `movimientos_inventario` (append-only).
- Crear una tabla `stock` separada **rompería** RNF-03 sin aportar valor.

### D-02 — Soft delete en todas las tablas operativas
Ninguna tabla del módulo permite `DELETE` físico. Se filtran con `WHERE deleted_at IS NULL`. El proyecto lo exige transversalmente (regla RNF ya documentada en `backend/app/shared/kernel/soft_delete.py:2`).

### D-03 — Snapshot del nombre de usuario en cada tabla
Siguiendo el patrón del Módulo C (`ventas.vendedor`, `anulaciones.realizado_por`, etc.), cada FK a `usuarios` viene acompañada de una columna `*_por_nombre VARCHAR(100) NOT NULL` con el `nombre` del usuario al momento de la operación. Esto **preserva el historial** si el nombre del usuario cambia o se borra lógicamente.

### D-04 — `ON DELETE RESTRICT` en todas las FKs hacia entidades con historial
Consistente con el resto del proyecto. No se puede borrar un usuario, categoría o producto que tenga movimientos, solicitudes, mermas o cambios de precio asociados.

### D-05 — Excepción: `detalle_solicitud.solicitud_id` usa `ON DELETE CASCADE`
La línea de detalle no existe sin su cabecera; si se borra (lógicamente) una solicitud, sus líneas también. Es la única `CASCADE` del módulo.

### D-06 — `historial_precios` es append-only
Nunca se hace `UPDATE` ni `DELETE`. El código de aplicación y (opcionalmente) un trigger `BEFORE UPDATE` lo refuerzan. Esto cumple HU-B11 ("los reportes históricos no se alteran").

### D-07 — `movimientos_inventario` también es append-only
Toda variación de stock deja un registro. `UPDATE`/`DELETE` están prohibidos por convención (no agrego CHECK porque la consulta de stock actual siempre lee de `productos.stock`).

### D-08 — `productos.precio` se mantiene por compatibilidad con el Módulo C
El Módulo C lee `productos.precio` por SQL directo. **No se renombra ni se elimina**. Las columnas nuevas (`precio_compra_actual`, `es_codigo_interno`, snapshots) se **agregan** sin tocar las existentes.

### D-09 — Doble control del flujo "solicitud no toca stock hasta aprobarse"
- En el **use case** que crea la solicitud: solo `INSERT` en `solicitudes_ingreso` y `detalle_solicitud`. No toca `productos.stock`.
- En el **use case** que aprueba: `UPDATE` de `solicitudes_ingreso.estado` + `INSERT` de `movimientos_inventario` + `UPDATE` de `productos.stock`, **todo en una sola transacción**. Si cualquier paso falla, `ROLLBACK`.

### D-10 — Código de barras vs código interno en una sola columna
`productos.codigo VARCHAR(60) UNIQUE` admite tanto el EAN-13 (12-13 dígitos) como el código interno (`PAP-001`). El flag `es_codigo_interno BOOLEAN` distingue el caso para validación de formato y para la lógica de "buscar por nombre" del POS (HU-B04).

### D-11 — `mermas.motivo` y `mermas.proveedor_id`
- `motivo` es `CHECK` con valores fijos: `vencimiento | rotura | otro`. Coincide con la regla de negocio "toda merma debe quedar diferenciada de una venta o de un robo" (RF-23, regla transversal).
- `proveedor_id` es **opcional** porque una merma puede ser de mercadería sin proveedor registrado.

### D-12 — Trazabilidad de deuda de proveedores con tabla histórica
- `proveedores.deuda_actual` se mantiene como **denormalizado controlado** para vistas rápidas (HU-B14).
- El historial completo está en `pagos_proveedor` (decisión validada con el equipo el 2026-07-19). Cada movimiento de deuda (compra a crédito o pago) deja una fila en esa tabla.
- Toda escritura en `deuda_actual` debe ir **dentro de la misma transacción** que inserta la fila correspondiente en `pagos_proveedor`. La invariante es: `deuda_actual = SUM(compra_credito) - SUM(pago)` (excluyendo soft-deleted).

### D-13 — Módulo C consume el Módulo B por SQL, no por HTTP
Decisión ya tomada en el proyecto (ver `backend/app/modules/modulo_c_ventas/infrastructure/adapters/integrations/sqlalchemy_stock_adapter.py`). **El Módulo B no expone un endpoint HTTP para descontar stock**. Solo expone:
- Endpoints HTTP **para el frontend** (catálogo, ingresos, mermas, etc.).
- Acceso SQL directo a `productos` para que C descuente de forma atómica (RNF-03).

### D-14 — Mermas con flujo de validación en dos pasos (cajero → admin)
Decisión validada con el equipo el 2026-07-19. El flujo es:
1. **Cualquier usuario autenticado** (ADMIN o CAJERO) puede **registrar** una merma. Esto crea la fila con `estado='Registrada'`, sin tocar stock.
2. **Solo ADMIN** puede **confirmar** (descuenta stock + crea movimiento) o **rechazar** (con motivo).
- Es la misma forma que el flujo de aprobación de ingresos (D-09): separar la detección del cambio de stock de su autorización, sin sacrificar agilidad para el cajero.
- Permite que el cajero reporte pérdidas en el momento sin esperar a la administradora, pero el impacto contable (descuento de stock) queda bajo control del ADMIN.

### D-15 — `pagos_proveedor` desde el día 1
Decisión validada con el equipo el 2026-07-19. Se crea la tabla histórica desde el inicio, no como "trabajo futuro". Razones:
- La conciliación de deudas y los reportes del Módulo D la requieren desde el primer día.
- Construir el historial de pagos desde el inicio es más barato que migrar datos después.
- La tabla es append-only por convención; el `soft delete` solo se permite por corrección administrativa.

---

## 6. Relación con otros módulos

### 6.1 Dependencia con Módulo A (Seguridad)

Este módulo **referencia** la tabla `usuarios` del Módulo A como FK externa. No la redefine ni la duplica. La convención del proyecto es:

- `usuarios.id` (`BIGSERIAL`) es la PK a la que se apunta.
- Todas las FKs usan `ON DELETE RESTRICT`.
- Toda columna de auditoría se **duplica** con un snapshot del `nombre` (ver D-03).

Los **permisos por rol** (RF transversal) se validan en backend consumiendo los endpoints del Módulo A (`/auth/...`, `/usuarios/...`) o importando su `require_permission`. Las reglas de este módulo:

| Operación | Rol permitido |
|---|---|
| `GET /productos`, `GET /categorias`, `GET /ingresos` (listar) | `ADMIN` y `CAJERO` |
| `POST /productos`, `PATCH /productos/{id}` (crear/editar) | `ADMIN` |
| `POST /ingresos` (crear solicitud) | `ADMIN` y `CAJERO` |
| `POST /ingresos/{id}/aprobar` | **`ADMIN` exclusivo** |
| `POST /ingresos/{id}/rechazar` | **`ADMIN` exclusivo** |
| `PATCH /productos/{id}/precio` | **`ADMIN` exclusivo** (HU-B11: el cajero no puede) |
| `POST /mermas` (registrar, paso 1, estado `Registrada`) | `ADMIN` y `CAJERO` (D-14) |
| `POST /mermas/{id}/confirmar` (paso 2, descuenta stock) | **`ADMIN` exclusivo** (D-14) |
| `POST /mermas/{id}/rechazar` (paso 2, sin tocar stock) | **`ADMIN` exclusivo** (D-14) |
| `* /proveedores` | `ADMIN` |
| `POST /proveedores/{id}/compras-credito` y `POST /proveedores/{id}/pagos` | `ADMIN` |

### 6.2 Dependencia cruzada con Módulo C (Ventas)

- **Lectura SQL directa**: C lee `productos` (`id`, `codigo`, `nombre`, `precio`, `stock`, `activo`, `deleted_at`) para validar y descontar.
- **FK física**: `detalles_venta.producto_id → productos.id` (declarada en `schema_modulo_c.sql`).
- **Compromiso**: cualquier cambio de estructura en `productos` debe coordinarse con Clever. Por eso D-08: solo se agregan columnas, no se modifican ni eliminan.

### 6.3 Dependencia con Módulo D (Documentos y reportes)

- D consumirá `movimientos_inventario` para reportes de actividad.
- D consumirá `historial_precios` para análisis de márgenes.
- D consumirá `mermas` para pérdidas.
- **Contrato de entrega**: D no toca estas tablas; solo las lee.

---

## 7. Decisiones validadas con el equipo (2026-07-19)

Todas las decisiones de diseño abiertas al inicio de esta documentación fueron resueltas en la sesión del 2026-07-19 con el dueño del módulo. Aplica la **regla del proyecto**: la documentación del repositorio es la fuente de verdad (ver `conventions/repo-over-prompt` en Engram).

| # | Punto | Resolución | Aplicado en |
|---|---|---|---|
| P-01 | Texto oficial de `RNF-02` | **No documentado en el repo**. Se mantiene la interpretación tentativa: rendimiento del POS/catálogo (≤1s respuesta). | `API_MODULO_B.md` §2.3. Se podrá ajustar cuando aparezca el texto oficial. |
| P-02 | Texto oficial de `RNF-06` | **No documentado en el repo**. Se mantiene la interpretación tentativa: disponibilidad/continuidad del inventario. | Documentado en las decisiones transversales; se ajustará cuando aparezca el texto oficial. |
| P-03 | Texto oficial de `RNF-09` | **No documentado en el repo**. Se mantiene la interpretación tentativa: seguridad de datos de inventario. | Documentado en las decisiones transversales; se ajustará cuando aparezca el texto oficial. |
| P-04 | Tabla `stock` separada en el prompt original | **No se crea**. Stock = `productos.stock` (regla del repo manda). | D-01. |
| P-05 | Política de mermas para cajero | **Cajero registra, ADMIN valida**. El cajero crea la merma con `estado='Registrada'` (no toca stock). ADMIN confirma (descuenta stock) o rechaza (con motivo). | D-14; tabla 4.8; DDL sección 6. |
| P-06 | Tabla `pagos_proveedor` para HU-B14 | **Se crea desde el día 1**. `deuda_actual` queda como denormalizado controlado, el historial completo vive en `pagos_proveedor`. | D-12, D-15; tabla 4.7; DDL sección 7. |
| P-07 | Storage de `foto_boleta_url` | **Supabase Storage**. URL pública con RLS o signed URL según el caso. | `API_MODULO_B.md` §8. |

---

## 8. Script DDL — `backend/db/schema_modulo_b_completo.sql`

> Este script es **aditivo e idempotente**. Se aplica con `python -m scripts.aplicar_schema` (ver `docs/SCRIPTS_DEV.md`). Asume que `schema_modulo_b_minimo.sql` y `schema_modulo_a.sql` ya están aplicados.

```sql
-- =============================================================================
-- Módulo B (COMPLETO) — Brayan
-- Catálogo, Inventario y Aprobación de Ingresos
-- Aditivo e idempotente. Se aplica con: python -m scripts.aplicar_schema
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Sección 1: Extensiones a tablas existentes
--   Solo ALTER TABLE ADD COLUMN IF NOT EXISTS. NO se modifican columnas
--   existentes (compromiso con Módulo C — RNF-03 atomicidad venta+stock).
-- -----------------------------------------------------------------------------

-- productos: precio de compra actual, flag de código interno, snapshots de auditoría
ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS precio_compra_actual  NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS es_codigo_interno     BOOLEAN        NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS creado_por            BIGINT,
    ADD COLUMN IF NOT EXISTS creado_por_nombre     VARCHAR(100),
    ADD COLUMN IF NOT EXISTS actualizado_por       BIGINT,
    ADD COLUMN IF NOT EXISTS actualizado_por_nombre VARCHAR(100);

ALTER TABLE productos
    ADD CONSTRAINT chk_productos_precio_compra_actual
        CHECK (precio_compra_actual >= 0)
        NOT VALID;

ALTER TABLE categorias
    ADD COLUMN IF NOT EXISTS creado_por        BIGINT,
    ADD COLUMN IF NOT EXISTS creado_por_nombre VARCHAR(100);

-- Índices faltantes en productos (búsqueda por nombre + alertas stock mínimo)
CREATE INDEX IF NOT EXISTS idx_productos_nombre
    ON productos (LOWER(nombre))
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_productos_activo_stock
    ON productos (activo, stock)
    WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- Sección 2: proveedores (HU-B14)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proveedores (
    id                  BIGSERIAL    PRIMARY KEY,
    razon_social        VARCHAR(120) NOT NULL,
    ruc                 VARCHAR(20),
    telefono            VARCHAR(20),
    email               VARCHAR(120),
    direccion           TEXT,
    activo              BOOLEAN      NOT NULL DEFAULT TRUE,
    deuda_actual        NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    deleted_by          BIGINT,
    creado_por          BIGINT       NOT NULL,
    creado_por_nombre   VARCHAR(100) NOT NULL,
    CONSTRAINT chk_proveedores_deuda_no_negativa CHECK (deuda_actual >= 0)
);

-- UNIQUE parcial sobre RUC (solo cuando no es NULL; permite informales sin RUC)
CREATE UNIQUE INDEX IF NOT EXISTS uq_proveedores_ruc
    ON proveedores (ruc)
    WHERE ruc IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_proveedores_razon
    ON proveedores (LOWER(razon_social))
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_proveedores_activo
    ON proveedores (activo)
    WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- Sección 3: solicitudes_ingreso (HU-B06, HU-B07, HU-B08)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_ingreso (
    id                       BIGSERIAL    PRIMARY KEY,
    proveedor_id             BIGINT,
    estado                   VARCHAR(20)  NOT NULL DEFAULT 'Pendiente',
    foto_boleta_url          TEXT         NOT NULL,
    motivo_rechazo           TEXT,
    solicitado_por           BIGINT       NOT NULL,
    solicitado_por_nombre    VARCHAR(100) NOT NULL,
    revisado_por             BIGINT,
    revisado_por_nombre      VARCHAR(100),
    revisado_en              TIMESTAMPTZ,
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at               TIMESTAMPTZ,
    deleted_by               BIGINT,
    CONSTRAINT chk_solicitudes_estado
        CHECK (estado IN ('Pendiente','Aprobada','Rechazada')),
    CONSTRAINT chk_solicitudes_rechazo_tiene_motivo
        CHECK (
            (estado = 'Rechazada' AND motivo_rechazo IS NOT NULL AND length(trim(motivo_rechazo)) > 0)
            OR estado <> 'Rechazada'
        ),
    CONSTRAINT chk_solicitudes_revisado_consistente
        CHECK (
            (estado = 'Pendiente' AND revisado_por IS NULL AND revisado_en IS NULL)
            OR (estado IN ('Aprobada','Rechazada') AND revisado_por IS NOT NULL AND revisado_en IS NOT NULL)
        ),
    CONSTRAINT fk_solicitudes_proveedor
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE RESTRICT,
    CONSTRAINT fk_solicitudes_solicitante
        FOREIGN KEY (solicitado_por) REFERENCES usuarios(id) ON DELETE RESTRICT,
    CONSTRAINT fk_solicitudes_revisor
        FOREIGN KEY (revisado_por) REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_solicitudes_estado
    ON solicitudes_ingreso (estado, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_solicitudes_solicitante
    ON solicitudes_ingreso (solicitado_por, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_solicitudes_proveedor
    ON solicitudes_ingreso (proveedor_id)
    WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- Sección 4: detalle_solicitud (líneas de la solicitud de ingreso)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detalle_solicitud (
    id                        BIGSERIAL       PRIMARY KEY,
    solicitud_id              BIGINT          NOT NULL,
    producto_id               BIGINT          NOT NULL,
    cantidad                  INT             NOT NULL,
    precio_compra_unitario    NUMERIC(10,2)   NOT NULL,
    created_at                TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT chk_detsol_cantidad_positiva  CHECK (cantidad > 0),
    CONSTRAINT chk_detsol_precio_no_negativo CHECK (precio_compra_unitario >= 0),
    CONSTRAINT fk_detsol_solicitud
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_ingreso(id) ON DELETE CASCADE,
    CONSTRAINT fk_detsol_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_detsol_solicitud
    ON detalle_solicitud (solicitud_id);

CREATE INDEX IF NOT EXISTS idx_detsol_producto
    ON detalle_solicitud (producto_id);

-- -----------------------------------------------------------------------------
-- Sección 5: movimientos_inventario (bitácora append-only)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id                        BIGSERIAL      PRIMARY KEY,
    producto_id               BIGINT         NOT NULL,
    cantidad                  INT            NOT NULL,
    tipo                      VARCHAR(20)    NOT NULL,
    motivo                    VARCHAR(200),
    solicitud_ingreso_id      BIGINT,
    merma_id                  BIGINT,
    created_at                TIMESTAMPTZ    NOT NULL DEFAULT now(),
    registrado_por            BIGINT         NOT NULL,
    registrado_por_nombre     VARCHAR(100)   NOT NULL,
    CONSTRAINT chk_mov_cantidad_no_cero  CHECK (cantidad <> 0),
    CONSTRAINT chk_mov_tipo
        CHECK (tipo IN ('ingreso','merma','ajuste','venta','devolucion')),
    CONSTRAINT chk_mov_signo_por_tipo CHECK (
        (tipo IN ('ingreso','devolucion') AND cantidad > 0) OR
        (tipo IN ('merma','venta')       AND cantidad < 0) OR
        (tipo = 'ajuste')
    ),
    CONSTRAINT chk_mov_ingreso_tiene_solicitud
        CHECK (tipo <> 'ingreso' OR solicitud_ingreso_id IS NOT NULL),
    CONSTRAINT chk_mov_merma_tiene_merma
        CHECK (
            tipo <> 'merma' OR (merma_id IS NOT NULL AND motivo IS NOT NULL AND length(trim(motivo)) > 0)
        ),
    CONSTRAINT fk_mov_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT,
    CONSTRAINT fk_mov_solicitud
        FOREIGN KEY (solicitud_ingreso_id) REFERENCES solicitudes_ingreso(id) ON DELETE RESTRICT,
    CONSTRAINT fk_mov_merma
        FOREIGN KEY (merma_id) REFERENCES mermas(id) ON DELETE RESTRICT,
    CONSTRAINT fk_mov_usuario
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_mov_producto_fecha
    ON movimientos_inventario (producto_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mov_tipo
    ON movimientos_inventario (tipo);

CREATE INDEX IF NOT EXISTS idx_mov_solicitud
    ON movimientos_inventario (solicitud_ingreso_id)
    WHERE solicitud_ingreso_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mov_merma
    ON movimientos_inventario (merma_id)
    WHERE merma_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Sección 6: mermas (HU-B12, RF-23) — flujo de validación en 2 pasos (D-14)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mermas (
    id                          BIGSERIAL    PRIMARY KEY,
    producto_id                 BIGINT       NOT NULL,
    cantidad                    INT          NOT NULL,
    motivo                      VARCHAR(30)  NOT NULL,
    observacion                 TEXT,
    proveedor_id                BIGINT,
    estado                      VARCHAR(20)  NOT NULL DEFAULT 'Registrada',
    motivo_rechazo              TEXT,
    registrado_por              BIGINT       NOT NULL,
    registrado_por_nombre       VARCHAR(100) NOT NULL,
    confirmado_por              BIGINT,
    confirmado_por_nombre       VARCHAR(100),
    confirmado_en               TIMESTAMPTZ,
    rechazado_por               BIGINT,
    rechazado_por_nombre        VARCHAR(100),
    rechazado_en                TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at                  TIMESTAMPTZ,
    deleted_by                  BIGINT,
    CONSTRAINT chk_mermas_cantidad_positiva  CHECK (cantidad > 0),
    CONSTRAINT chk_mermas_motivo
        CHECK (motivo IN ('vencimiento','rotura','otro')),
    CONSTRAINT chk_mermas_estado
        CHECK (estado IN ('Registrada','Confirmada','Rechazada')),
    CONSTRAINT chk_mermas_estado_consistente CHECK (
        (estado = 'Registrada'  AND confirmado_por IS NULL AND confirmado_en IS NULL AND rechazado_por IS NULL AND rechazado_en IS NULL AND motivo_rechazo IS NULL) OR
        (estado = 'Confirmada'  AND confirmado_por IS NOT NULL AND confirmado_en IS NOT NULL AND rechazado_por IS NULL AND rechazado_en IS NULL AND motivo_rechazo IS NULL) OR
        (estado = 'Rechazada'   AND rechazado_por IS NOT NULL AND rechazado_en IS NOT NULL AND motivo_rechazo IS NOT NULL AND length(trim(motivo_rechazo)) >= 5 AND confirmado_por IS NULL AND confirmado_en IS NULL)
    ),
    CONSTRAINT fk_mermas_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT,
    CONSTRAINT fk_mermas_proveedor
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE RESTRICT,
    CONSTRAINT fk_mermas_registrado_por
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id) ON DELETE RESTRICT,
    CONSTRAINT fk_mermas_confirmado_por
        FOREIGN KEY (confirmado_por) REFERENCES usuarios(id) ON DELETE RESTRICT,
    CONSTRAINT fk_mermas_rechazado_por
        FOREIGN KEY (rechazado_por) REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_mermas_producto_fecha
    ON mermas (producto_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_mermas_motivo
    ON mermas (motivo)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_mermas_estado
    ON mermas (estado, created_at DESC)
    WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- Sección 7: pagos_proveedor (HU-B14) — historial de deuda (D-12, D-15)
--   Decisión validada 2026-07-19: trazabilidad desde el día 1, no denormalizado.
--   Cada compra a crédito (tipo='compra_credito') o pago (tipo='pago') deja
--   una fila. proveedores.deuda_actual se mantiene consistente con la fórmula:
--     deuda_actual = SUM(monto WHERE tipo='compra_credito' AND deleted_at IS NULL)
--                  - SUM(monto WHERE tipo='pago' AND deleted_at IS NULL)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos_proveedor (
    id                          BIGSERIAL     PRIMARY KEY,
    proveedor_id                BIGINT        NOT NULL,
    tipo                        VARCHAR(20)   NOT NULL,
    monto                       NUMERIC(12,2) NOT NULL,
    concepto                    TEXT,
    fecha                       DATE          NOT NULL,
    solicitud_ingreso_id        BIGINT,
    created_at                  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at                  TIMESTAMPTZ,
    deleted_by                  BIGINT,
    registrado_por              BIGINT        NOT NULL,
    registrado_por_nombre       VARCHAR(100)  NOT NULL,
    CONSTRAINT chk_pagos_monto_positivo  CHECK (monto > 0),
    CONSTRAINT chk_pagos_tipo
        CHECK (tipo IN ('compra_credito','pago')),
    CONSTRAINT chk_pagos_solicitud_solo_en_compra
        CHECK (tipo = 'compra_credito' OR solicitud_ingreso_id IS NULL),
    CONSTRAINT fk_pagos_proveedor
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE RESTRICT,
    CONSTRAINT fk_pagos_solicitud
        FOREIGN KEY (solicitud_ingreso_id) REFERENCES solicitudes_ingreso(id) ON DELETE RESTRICT,
    CONSTRAINT fk_pagos_usuario
        FOREIGN KEY (registrado_por) REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_pagos_proveedor
    ON pagos_proveedor (proveedor_id, fecha DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pagos_tipo
    ON pagos_proveedor (tipo)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pagos_solicitud
    ON pagos_proveedor (solicitud_ingreso_id)
    WHERE solicitud_ingreso_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Sección 8: historial_precios (HU-B11, append-only)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historial_precios (
    id                       BIGSERIAL     PRIMARY KEY,
    producto_id              BIGINT        NOT NULL,
    precio_anterior          NUMERIC(10,2),
    precio_nuevo             NUMERIC(10,2) NOT NULL,
    tipo_precio              VARCHAR(20)   NOT NULL,
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT now(),
    modificado_por           BIGINT        NOT NULL,
    modificado_por_nombre    VARCHAR(100)  NOT NULL,
    CONSTRAINT chk_historial_precio_no_negativo CHECK (precio_nuevo >= 0),
    CONSTRAINT chk_historial_tipo
        CHECK (tipo_precio IN ('venta','compra')),
    CONSTRAINT fk_historial_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT,
    CONSTRAINT fk_historial_usuario
        FOREIGN KEY (modificado_por) REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_historial_producto_fecha
    ON historial_precios (producto_id, tipo_precio, created_at DESC);

-- -----------------------------------------------------------------------------
-- Sección 9: Trigger opcional para reforzar inmutabilidad de historial_precios
--   Segunda línea de defensa. La principal es la convención del código.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_historial_precios_inmutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'historial_precios es append-only; UPDATE/DELETE prohibidos (RF-18, HU-B11)';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_historial_precios_no_update ON historial_precios;
CREATE TRIGGER trg_historial_precios_no_update
    BEFORE UPDATE OR DELETE ON historial_precios
    FOR EACH ROW EXECUTE FUNCTION trg_historial_precios_inmutable();

-- =============================================================================
-- Fin del script. Tras aplicar:
--   1. Verificar con \dt modulo_b_* y \d productos.
--   2. Confirmar que el Módulo C sigue funcionando (sus tests de integración).
--   3. Actualizar `docs/Cambios-Brayan/ER_MODULO_B.md` si se ajustó algo.
-- =============================================================================
```

### 8.1 Orden de aplicación

Como las tablas tienen FKs cruzadas, el orden de creación importa:

1. `proveedores` (no depende de nadie del módulo).
2. `solicitudes_ingreso` (depende de `proveedores` + `usuarios`).
3. `detalle_solicitud` (depende de `solicitudes_ingreso` + `productos`).
4. `mermas` (depende de `productos` + `proveedores` + `usuarios`).
5. `pagos_proveedor` (depende de `proveedores` + `solicitudes_ingreso` + `usuarios`).
6. `movimientos_inventario` (depende de `productos` + `solicitudes_ingreso` + `mermas` + `usuarios`).
7. `historial_precios` (depende de `productos` + `usuarios`).

El script ya respeta este orden dentro del archivo.

### 8.2 Cómo aplicar

```bash
# 1. Asegurarse de que schema_modulo_b_minimo.sql y schema_modulo_a.sql ya están aplicados.
# 2. Renombrar o copiar el script a la carpeta esperada:
cp docs/Cambios-Brayan/ER_MODULO_B.md backend/db/schema_modulo_b_completo.sql
# (en la práctica, el SQL va en backend/db/, este MD solo lo embebe como referencia)

# 3. Aplicar:
cd backend
python -m scripts.aplicar_schema modulo_b_completo
```

> **Decisión operativa**: el script `.sql` debe vivir en `backend/db/` (es donde busca `aplicar_schema.py`). El bloque de arriba se copia tal cual a ese archivo. El `.md` lo mantiene legible y versionado para revisión.

---

## 9. Resumen ejecutivo

- **7 tablas nuevas** a crear: `proveedores`, `solicitudes_ingreso`, `detalle_solicitud`, `mermas`, `pagos_proveedor`, `movimientos_inventario`, `historial_precios`.
- **2 tablas existentes** que **no se tocan**: `productos`, `categorias` (compromiso con Módulo C).
- **Extensiones aditivas** a `productos` y `categorias` con `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (sin romper a C).
- **FK externa** a `usuarios` del Módulo A con `ON DELETE RESTRICT` + snapshot del nombre.
- **DDL idempotente**, alineado con `schema_modulo_a.sql` y `schema_modulo_c.sql`.
- **7 decisiones validadas** con el equipo el 2026-07-19 (ver sección 7).
- **Documentos relacionados**: `CASOS_DE_USO_MODULO_B.md` y `API_MODULO_B.md` (misma carpeta).
