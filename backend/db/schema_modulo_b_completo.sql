-- ============================================================================
-- Módulo B (COMPLETO) — Brayan
-- Catálogo, Inventario y Aprobación de Ingresos
-- Aditivo e idempotente. Se aplica con: python -m scripts.aplicar_schema modulo_b_completo
-- Asume que `schema_modulo_b_minimo.sql` y `schema_modulo_a.sql` ya están aplicados.
-- NO se aplica automáticamente desde este PR — el usuario lo ejecuta contra
-- Supabase cuando lo decida (ver `docs/Cambios-Brayan/ER_MODULO_B.md` §8.2).
-- ============================================================================

-- -----------------------------------------------------------------------------
-- Sección 1: Extensiones a tablas existentes
--   Solo ALTER TABLE ADD COLUMN IF NOT EXISTS. NO se modifican columnas
--   existentes (compromiso con Módulo C — RNF-03 atomicidad venta+stock).
-- -----------------------------------------------------------------------------

-- productos: precio de compra actual, flag de código interno, foto, snapshots
ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS precio_compra_actual   NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS es_codigo_interno      BOOLEAN        NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS foto_url               TEXT,
    -- HU-B13: alerta única de stock mínimo (se rearma al reponer).
    ADD COLUMN IF NOT EXISTS alerta_stock_notificada BOOLEAN       NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS creado_por             BIGINT,
    ADD COLUMN IF NOT EXISTS creado_por_nombre      VARCHAR(100),
    ADD COLUMN IF NOT EXISTS actualizado_por        BIGINT,
    ADD COLUMN IF NOT EXISTS actualizado_por_nombre VARCHAR(100);

-- categorías: descripción + auditoría + soft delete
ALTER TABLE categorias
    ADD COLUMN IF NOT EXISTS descripcion    TEXT,
    ADD COLUMN IF NOT EXISTS creado_por     BIGINT,
    ADD COLUMN IF NOT EXISTS creado_por_nombre VARCHAR(100),
    ADD COLUMN IF NOT EXISTS created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS deleted_at     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by     BIGINT;

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
-- Sección 5: mermas (HU-B12, RF-23) — flujo de validación en 2 pasos (D-14)
--   Creada ANTES de movimientos_inventario porque ese le hace FK.
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
-- Sección 6: movimientos_inventario (bitácora append-only)
--   Depende de mermas (FK a mermas.id), por eso se crea después.
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
--   Segunda línea de defensa. La principal es la convención del código (D-06).
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
-- Sección 10: Permisos nuevos del Módulo B + asignación idempotente a roles
--   Decisión cerrada en sesión 2026-07-19 (ver `sdd/modulo-b-catalogo/proposal`):
--     - 8 permisos nuevos a crear
--     - ADMIN recibe los 8 nuevos (los 20 existentes ya los tiene)
--     - CAJERO recibe los 2 nuevos que le aplican + se re-confirman los 2 viejos
-- =============================================================================

-- 8 permisos nuevos del Módulo B
INSERT INTO permisos (codigo, descripcion) VALUES
    ('mermas.registrar',            'Registrar mermas y pérdidas (paso 1, estado Registrada)'),
    ('mermas.confirmar',            'Confirmar o rechazar mermas (paso 2, descuenta stock o no)'),
    ('proveedores.gestionar',       'Alta, edición y consulta de proveedores'),
    ('proveedores.compras_credito', 'Registrar compras a crédito que aumentan la deuda'),
    ('proveedores.pagos',           'Registrar pagos a proveedor que disminuyen la deuda'),
    ('categorias.gestionar',        'Alta y edición de categorías de productos'),
    ('storage.upload',              'Subir archivos a Supabase Storage (boletas, fotos de producto)'),
    ('historial_precios.ver',       'Consultar el historial de cambios de precio'),
    -- Faltaba: los routers de proveedores lo exigen (listado y detalle).
    ('proveedores.ver',             'Ver el listado y el detalle de proveedores')
ON CONFLICT (codigo) DO NOTHING;

-- Asignación idempotente: ADMIN recibe los 8 nuevos
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permisos p
WHERE r.nombre = 'ADMIN'
  AND p.codigo IN (
      'mermas.registrar','mermas.confirmar',
      'proveedores.gestionar','proveedores.compras_credito','proveedores.pagos',
      'proveedores.ver',
      'categorias.gestionar','storage.upload','historial_precios.ver'
  )
ON CONFLICT (rol_id, permiso_id) DO NOTHING;

-- Asignación idempotente: CAJERO recibe los 4 que le aplican.
-- Los 2 nuevos (mermas.registrar, storage.upload) son del Módulo B;
-- los 2 viejos (inventario.solicitar_ingreso, inventario.ver) se re-confirman
-- por si la corrida anterior no los había asignado.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permisos p
WHERE r.nombre = 'CAJERO'
  AND p.codigo IN (
      'inventario.solicitar_ingreso',
      'inventario.ver',
      'mermas.registrar',
      'storage.upload',
      'proveedores.ver'
  )
ON CONFLICT (rol_id, permiso_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Sección 3.5 (sdd/modulo-b-aprobaciones-detalle-editar):
--   Edit audit fields + free-text motivo on solicitudes_ingreso.
--   Idempotent (ADD COLUMN IF NOT EXISTS, CREATE INDEX IF NOT EXISTS).
-- -----------------------------------------------------------------------------
ALTER TABLE solicitudes_ingreso
    ADD COLUMN IF NOT EXISTS motivo             TEXT,
    ADD COLUMN IF NOT EXISTS editado_por        BIGINT,
    ADD COLUMN IF NOT EXISTS editado_por_nombre VARCHAR(100),
    ADD COLUMN IF NOT EXISTS editado_en         TIMESTAMPTZ;

-- FK del editor (SET NULL on user delete — softer than revisado_por's RESTRICT
-- porque editar es colaborativo; perder el user no debe invalidar la fila).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_solicitudes_editado_por'
          AND table_name = 'solicitudes_ingreso'
    ) THEN
        ALTER TABLE solicitudes_ingreso
            ADD CONSTRAINT fk_solicitudes_editado_por
            FOREIGN KEY (editado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_solicitudes_editado_en
    ON solicitudes_ingreso (editado_en DESC)
    WHERE editado_en IS NOT NULL AND deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- Sección 5.5 (sdd/modulo-b-aprobaciones-detalle-editar):
--   Edit audit fields on mermas. NO `motivo` column (the existing motivo
--   column is the enum `vencimiento | rotura | otro`).
-- -----------------------------------------------------------------------------
ALTER TABLE mermas
    ADD COLUMN IF NOT EXISTS editado_por        BIGINT,
    ADD COLUMN IF NOT EXISTS editado_por_nombre VARCHAR(100),
    ADD COLUMN IF NOT EXISTS editado_en         TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_mermas_editado_por'
          AND table_name = 'mermas'
    ) THEN
        ALTER TABLE mermas
            ADD CONSTRAINT fk_mermas_editado_por
            FOREIGN KEY (editado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_mermas_editado_en
    ON mermas (editado_en DESC)
    WHERE editado_en IS NOT NULL AND deleted_at IS NULL;

-- =============================================================================
-- Fin del script. Tras aplicar:
--   1. Verificar con \dt public.* y \d productos.
--   2. Confirmar que el Módulo C sigue funcionando (sus tests de integración).
--   3. Actualizar `docs/Cambios-Brayan/ER_MODULO_B.md` si se ajustó algo.
-- =============================================================================
