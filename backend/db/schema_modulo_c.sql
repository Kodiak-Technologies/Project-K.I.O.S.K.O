-- ============================================================================
-- MÓDULO C — Ventas, Caja y Punto de Venta (POS) · Responsable: CLEVER
-- Script DDL (SOL-03-C). Idempotente: se puede ejecutar varias veces.
-- Se aplica con:  python -m scripts.aplicar_schema modulo_c
-- (la BD compartida tiene una línea de migraciones de otra rama, por eso el
--  módulo se aplica con este script y no con alembic; ver scripts/aplicar_schema.py)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Limpieza de placeholders: la rama del módulo D creó versiones provisionales
--    de ventas/detalles_venta/turnos_caja (con enums) para probar sus boletas.
--    Se detectan por el tipo de la columna estado/metodo_pago (USER-DEFINED).
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'turnos_caja' AND column_name = 'estado'
          AND data_type = 'USER-DEFINED'
    ) THEN
        DROP TABLE IF EXISTS detalles_venta CASCADE;
        DROP TABLE IF EXISTS ventas CASCADE;
        DROP TABLE IF EXISTS turnos_caja CASCADE;
        DROP TYPE IF EXISTS estado_caja;
        DROP TYPE IF EXISTS metodo_pago;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 1. TURNOS_CAJA (HU-C06): apertura manual con el efectivo inicial contado.
--    Apertura y cierre visibles para todos los usuarios (cambio de turno).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS turnos_caja (
    id                 BIGSERIAL PRIMARY KEY,
    usuario_id         BIGINT       NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    abierto_por        VARCHAR(100) NOT NULL,             -- snapshot del nombre
    monto_inicial      NUMERIC(10,2) NOT NULL,
    estado             VARCHAR(10)  NOT NULL DEFAULT 'ABIERTO',  -- ABIERTO | CERRADO
    abierto_en         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    cerrado_en         TIMESTAMPTZ,
    monto_final        NUMERIC(10,2),                     -- efectivo REAL contado al cierre
    usuario_cierre_id  BIGINT       REFERENCES usuarios(id) ON DELETE RESTRICT,
    cerrado_por        VARCHAR(100),
    CONSTRAINT ck_turnos_monto_inicial_no_negativo CHECK (monto_inicial >= 0)
);

-- Una sola caja física: no puede haber dos turnos ABIERTOs a la vez.
CREATE UNIQUE INDEX IF NOT EXISTS ux_turnos_caja_abierto
    ON turnos_caja (estado) WHERE estado = 'ABIERTO';

-- ----------------------------------------------------------------------------
-- 2. VENTAS y DETALLES_VENTA (HU-C01): registro de la venta del POS.
--    nombre/precio_unitario son SNAPSHOT: cambiar un precio hoy no altera
--    los reportes históricos (RF-18).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ventas (
    id                BIGSERIAL PRIMARY KEY,
    turno_id          BIGINT        NOT NULL REFERENCES turnos_caja(id) ON DELETE RESTRICT,
    usuario_id        BIGINT        NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    vendedor          VARCHAR(100)  NOT NULL,            -- snapshot del nombre
    total             NUMERIC(10,2) NOT NULL,
    metodo_pago       VARCHAR(20)   NOT NULL,            -- resumen (MIXTO si hay varios)
    estado            VARCHAR(20)   NOT NULL DEFAULT 'COMPLETADA',  -- COMPLETADA | ANULADA | DEVUELTA_PARCIAL
    motivo_anulacion  TEXT,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ventas_created_at ON ventas (created_at);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_id   ON ventas (turno_id);

CREATE TABLE IF NOT EXISTS detalles_venta (
    id                 BIGSERIAL PRIMARY KEY,
    venta_id           BIGINT        NOT NULL REFERENCES ventas(id) ON DELETE RESTRICT,
    producto_id        BIGINT        NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    nombre             VARCHAR(150)  NOT NULL,            -- snapshot
    precio_unitario    NUMERIC(10,2) NOT NULL,            -- snapshot
    cantidad           INTEGER       NOT NULL,
    cantidad_devuelta  INTEGER       NOT NULL DEFAULT 0,
    CONSTRAINT ck_detalles_cantidad_positiva CHECK (cantidad > 0)
);

CREATE INDEX IF NOT EXISTS ix_detalles_venta_venta_id ON detalles_venta (venta_id);

-- ----------------------------------------------------------------------------
-- 3. METODOS_PAGO y PAGOS_VENTA (HU-C04): catálogo gestionable por el ADMIN y
--    pagos por venta (una venta mixta tiene varios pagos). es_efectivo separa
--    el dinero FÍSICO del digital: el arqueo (RF-17) solo cuadra efectivo.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS metodos_pago (
    id           SERIAL PRIMARY KEY,
    codigo       VARCHAR(20) NOT NULL UNIQUE,   -- EFECTIVO | YAPE | PLIN | ...
    nombre       VARCHAR(50) NOT NULL,
    es_efectivo  BOOLEAN     NOT NULL DEFAULT FALSE,
    activo       BOOLEAN     NOT NULL DEFAULT TRUE
);

INSERT INTO metodos_pago (codigo, nombre, es_efectivo, activo) VALUES
    ('EFECTIVO',      'Efectivo',      TRUE,  TRUE),
    ('YAPE',          'Yape',          FALSE, TRUE),
    ('PLIN',          'Plin',          FALSE, TRUE),
    ('TARJETA',       'Tarjeta',       FALSE, TRUE),
    ('TRANSFERENCIA', 'Transferencia', FALSE, TRUE)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS pagos_venta (
    id              BIGSERIAL PRIMARY KEY,
    venta_id        BIGINT        NOT NULL REFERENCES ventas(id) ON DELETE RESTRICT,
    metodo_pago_id  INTEGER       NOT NULL REFERENCES metodos_pago(id) ON DELETE RESTRICT,
    codigo_metodo   VARCHAR(20)   NOT NULL,     -- snapshot para el historial
    es_efectivo     BOOLEAN       NOT NULL DEFAULT FALSE,
    monto           NUMERIC(10,2) NOT NULL,
    monto_recibido  NUMERIC(10,2),              -- solo efectivo: para el vuelto
    CONSTRAINT ck_pagos_monto_positivo CHECK (monto > 0)
);

CREATE INDEX IF NOT EXISTS ix_pagos_venta_venta_id ON pagos_venta (venta_id);
