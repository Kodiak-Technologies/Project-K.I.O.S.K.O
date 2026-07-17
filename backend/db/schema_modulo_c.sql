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
