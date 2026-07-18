-- DDL: Módulo D — Documentos (Boletas/Drive, Reportes, Notificaciones, Respaldos)
-- Base de datos: PostgreSQL 16
-- Generado a partir de los modelos SQLAlchemy

-- ============================================================
-- Tabla: boletas_clientes
-- ============================================================
CREATE TABLE IF NOT EXISTS boletas_clientes (
    id              BIGSERIAL       PRIMARY KEY,
    venta_id        BIGINT          NOT NULL UNIQUE,
    numero          VARCHAR(20)     NOT NULL UNIQUE,
    total           NUMERIC(12,2)   NOT NULL,
    emitida_en      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    url_pdf         TEXT,
    cliente_nombre  VARCHAR(120)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_boletas_clientes_numero
    ON boletas_clientes (numero);

-- ============================================================
-- Tabla: archivos_drive
-- ============================================================
CREATE TABLE IF NOT EXISTS archivos_drive (
    id              BIGSERIAL       PRIMARY KEY,
    boleta_id       BIGINT          NOT NULL
                    REFERENCES boletas_clientes(id) ON DELETE RESTRICT,
    archivo_nombre  VARCHAR(255)    NOT NULL,
    carpeta         VARCHAR(255)    NOT NULL DEFAULT '',
    estado          VARCHAR(20)     NOT NULL DEFAULT 'PENDIENTE',
    intentos        INTEGER         NOT NULL DEFAULT 0,
    drive_file_id   VARCHAR(255),
    error_mensaje   TEXT,
    creado_en       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_archivos_drive_boleta_id
    ON archivos_drive (boleta_id);
CREATE INDEX IF NOT EXISTS ix_archivos_drive_estado
    ON archivos_drive (estado);

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
    usuario_id      BIGINT,
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
    id                      INTEGER     PRIMARY KEY DEFAULT 1,
    canal_telegram_activo   BOOLEAN     NOT NULL DEFAULT TRUE,
    canal_correo_activo     BOOLEAN     NOT NULL DEFAULT FALSE,
    nivel_detalle           VARCHAR(20) NOT NULL DEFAULT 'MEDIO',
    telegram_chat_id        VARCHAR(100),
    correo_destino          VARCHAR(120),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
