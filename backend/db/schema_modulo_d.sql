-- ============================================================================
-- SCHEMA DDL — MÓDULO D: Documentos (Boletas/Drive), Reportes,
--              Notificaciones e Infraestructura
-- PostgreSQL (Cloud SQL). Zona horaria de referencia: America/Lima.
-- NOTA: la fuente de verdad de las migraciones es Alembic (backend/alembic/).
-- Este archivo es la referencia comentada para revisión y para pgAdmin.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Tablas
-- ---------------------------------------------------------------------------

-- Boletas digitales generadas para cada venta confirmada.
-- Una venta solo genera una boleta (venta_id UNIQUE).
CREATE TABLE boletas_clientes (
    id          BIGSERIAL PRIMARY KEY,
    venta_id    BIGINT       NOT NULL UNIQUE,          -- FK → ventas.id (Module C)
    numero      VARCHAR(20)  NOT NULL UNIQUE,          -- formato B001-NNNNNN
    total       NUMERIC(12,2) NOT NULL,                -- monto total de la venta
    emitida_en  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    url_pdf     TEXT                                  -- URL en Google Drive (nullable)
);
CREATE INDEX ix_boletas_venta_id     ON boletas_clientes (venta_id);
CREATE INDEX ix_boletas_numero       ON boletas_clientes (numero);
CREATE INDEX ix_boletas_emitida_en   ON boletas_clientes (emitida_en);

-- Control de subida de archivos a Google Drive.
-- Registra cada intento y su estado.
CREATE TABLE archivos_drive (
    id              BIGSERIAL PRIMARY KEY,
    boleta_id       BIGINT       NOT NULL REFERENCES boletas_clientes(id) ON DELETE RESTRICT,
    archivo_nombre  VARCHAR(255) NOT NULL,             -- nombre del archivo subido
    carpeta         VARCHAR(255) NOT NULL DEFAULT '',  -- ej: boletas/2026/07/
    estado          VARCHAR(20)  NOT NULL DEFAULT 'PENDIENTE',  -- PENDIENTE | SUBIDO | FALLIDO
    intentos        INT          NOT NULL DEFAULT 0,
    drive_file_id   VARCHAR(255),                      -- ID en Google Drive (nullable)
    error_mensaje   TEXT,                              -- último error (nullable)
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_archivos_drive_boleta_id ON archivos_drive (boleta_id);
CREATE INDEX ix_archivos_drive_estado    ON archivos_drive (estado);

-- Notificaciones del sistema (stock bajo, cierre de caja, solicitudes, etc.).
-- No tiene borrado lógico; se purgan después de 30 días (RNF-14).
CREATE TABLE notificaciones (
    id              BIGSERIAL PRIMARY KEY,
    tipo            VARCHAR(30)  NOT NULL,             -- STOCK_BAJO | CIERRE_CAJA | SOLICITUD_INGRESO
    titulo          VARCHAR(120) NOT NULL,
    mensaje         TEXT         NOT NULL,
    leida           BOOLEAN      NOT NULL DEFAULT FALSE,
    entidad_origen  VARCHAR(60),                       -- tabla que originó la notificación (nullable)
    entidad_id      VARCHAR(60),                       -- ID de la entidad origen (nullable)
    usuario_id      BIGINT,                            -- FK → usuarios.id (Module A), nullable
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_notificaciones_leida      ON notificaciones (leida);
CREATE INDEX ix_notificaciones_created_at ON notificaciones (created_at);
CREATE INDEX ix_notificaciones_tipo       ON notificaciones (tipo);

-- Configuración de canales de notificación (fila única id=1, como configuracion_negocio).
-- Solo ADMIN la edita.
CREATE TABLE config_notificaciones (
    id                       INT PRIMARY KEY DEFAULT 1, -- siempre 1
    canal_telegram_activo    BOOLEAN      NOT NULL DEFAULT TRUE,
    canal_correo_activo      BOOLEAN      NOT NULL DEFAULT FALSE,
    nivel_detalle            VARCHAR(20)  NOT NULL DEFAULT 'MEDIO',  -- BAJO | MEDIO | ALTO
    telegram_chat_id         VARCHAR(100),                           -- nullable
    correo_destino           VARCHAR(120),                           -- nullable
    updated_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Registro de copias de seguridad (backups) de la base de datos.
-- Los respaldos expiran después de 30 días.
CREATE TABLE respaldos (
    id              BIGSERIAL PRIMARY KEY,
    archivo_nombre  VARCHAR(255) NOT NULL,             -- ej: tienda_sistema_20260714_020000.dump
    tamano_bytes    BIGINT       NOT NULL DEFAULT 0,   -- tamaño del archivo
    estado          VARCHAR(20)  NOT NULL DEFAULT 'PENDIENTE',  -- PENDIENTE | COMPLETADO | FALLIDO
    generado_en     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expira_en       TIMESTAMPTZ  NOT NULL DEFAULT (NOW() + INTERVAL '30 days')
);
CREATE INDEX ix_respaldos_estado       ON respaldos (estado);
CREATE INDEX ix_respaldos_generado_en  ON respaldos (generado_en);

-- ---------------------------------------------------------------------------
-- 2. Seed mínimo (la versión completa es backend/scripts/seed.py)
-- ---------------------------------------------------------------------------
INSERT INTO config_notificaciones (id) VALUES (1);
