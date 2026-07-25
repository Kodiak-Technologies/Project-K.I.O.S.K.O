-- DDL: Módulo D — Documentos (Reportes, Notificaciones, Respaldos)
-- Base de datos: PostgreSQL 16
-- Generado a partir de los modelos SQLAlchemy (post migración 0012)

-- ============================================================
-- Tabla: notificaciones
-- ============================================================
CREATE TABLE IF NOT EXISTS notificaciones (
    id              BIGSERIAL       PRIMARY KEY,
    tipo            VARCHAR(30)     NOT NULL,
    titulo          VARCHAR(120)    NOT NULL,
    mensaje         TEXT            NOT NULL,
    leida           BOOLEAN         NOT NULL DEFAULT FALSE,
    entidad_origen  VARCHAR(60),
    entidad_id      VARCHAR(60),
    usuario_id      BIGINT          REFERENCES usuarios(id) ON DELETE SET NULL,
    producto_id     BIGINT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notificaciones_leida
    ON notificaciones (leida);
CREATE INDEX IF NOT EXISTS ix_notificaciones_created_at
    ON notificaciones (created_at);
CREATE INDEX IF NOT EXISTS ix_notificaciones_tipo
    ON notificaciones (tipo);

-- ============================================================
-- Tabla: config_notificaciones (fila única, id=1)
-- ============================================================
CREATE TABLE IF NOT EXISTS config_notificaciones (
    id              INTEGER     PRIMARY KEY DEFAULT 1,
    nivel_detalle   VARCHAR(20) NOT NULL DEFAULT 'BAJO',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insertar fila por defecto si no existe
INSERT INTO config_notificaciones (id) VALUES (1)
    ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- Tabla: respaldos
-- ============================================================
CREATE TABLE IF NOT EXISTS respaldos (
    id              BIGSERIAL       PRIMARY KEY,
    archivo_nombre  VARCHAR(255)    NOT NULL,
    tamano_bytes    BIGINT          NOT NULL DEFAULT 0,
    estado          VARCHAR(20)     NOT NULL DEFAULT 'PENDIENTE',
    generado_en     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expira_en       TIMESTAMPTZ     NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_respaldos_estado
    ON respaldos (estado);
CREATE INDEX IF NOT EXISTS ix_respaldos_generado_en
    ON respaldos (generado_en);

-- ============================================================
-- Tabla: oauth_tokens
-- ============================================================
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id                  BIGSERIAL       PRIMARY KEY,
    proveedor           VARCHAR(50)     NOT NULL,
    access_token        TEXT            NOT NULL,
    refresh_token       TEXT            NOT NULL,
    token_expiry        TIMESTAMPTZ,
    usuario_id          BIGINT,
    fecha_creacion      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_oauth_tokens_proveedor
    ON oauth_tokens (proveedor);
