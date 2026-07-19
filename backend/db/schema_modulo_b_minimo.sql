-- ============================================================================
-- Módulo B (MÍNIMO) — productos y categorías para habilitar el POS del Módulo C
-- Implementación temporal (Clever) según docs/FRONTEND_CONTRATOS_API.md.
-- Idempotente: se puede ejecutar varias veces sin romper nada.
-- Equivalente a la migración alembic 0002_modulo_b_productos_minimo
-- (la BD compartida tiene una línea de migraciones distinta a esta rama,
--  por eso el módulo se aplica con este script: ver scripts/aplicar_schema.py).
-- ============================================================================

CREATE TABLE IF NOT EXISTS categorias (
    id      SERIAL PRIMARY KEY,
    nombre  VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS productos (
    id            BIGSERIAL PRIMARY KEY,
    codigo        VARCHAR(60)  NOT NULL UNIQUE,          -- código de barras o interno (PAP-001)
    nombre        VARCHAR(150) NOT NULL,
    categoria_id  INTEGER      REFERENCES categorias(id) ON DELETE RESTRICT,
    precio        NUMERIC(10,2) NOT NULL,
    stock         INTEGER      NOT NULL DEFAULT 0,
    stock_minimo  INTEGER      NOT NULL DEFAULT 0,
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    -- Borrado lógico transversal (nada se elimina físicamente)
    deleted_at    TIMESTAMPTZ,
    deleted_by    BIGINT,
    -- El stock nunca queda negativo (RF-08)
    CONSTRAINT ck_productos_stock_no_negativo CHECK (stock >= 0)
);

CREATE INDEX IF NOT EXISTS ix_productos_codigo ON productos (codigo);
CREATE INDEX IF NOT EXISTS ix_productos_nombre ON productos (nombre);
