-- ============================================================================
-- SCHEMA DDL — MÓDULO A: Seguridad, Accesos, Configuración y Auditoría
-- PostgreSQL (Cloud SQL). Zona horaria de referencia: America/Lima.
-- NOTA: la fuente de verdad de las migraciones es Alembic (backend/alembic/).
-- Este archivo es la referencia comentada para revisión y para pgAdmin.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Usuarios de base de datos (principio de mínimo privilegio)
--    Ejecutar como superusuario. Reemplazar las contraseñas por valores seguros.
-- ---------------------------------------------------------------------------
-- Usuario de la aplicación (Cloud Run): NO es superusuario.
CREATE ROLE app_kiosko LOGIN PASSWORD 'CAMBIAR_ME_APP';
-- Usuario de solo lectura para consultas desde pgAdmin:
CREATE ROLE lectura_pgadmin LOGIN PASSWORD 'CAMBIAR_ME_LECTURA';

-- ---------------------------------------------------------------------------
-- 2. Tablas
-- ---------------------------------------------------------------------------

-- Roles del sistema: ADMIN (dueña) y CAJERO (vendedores).
CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(30)  NOT NULL UNIQUE,          -- 'ADMIN' | 'CAJERO'
    descripcion VARCHAR(255) NOT NULL DEFAULT ''
);

-- Catálogo de permisos por acción (viven en BD para ajustarlos sin redeploy).
CREATE TABLE permisos (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(60)  NOT NULL UNIQUE,          -- ej. 'ventas.anular'
    descripcion VARCHAR(255) NOT NULL DEFAULT ''
);

-- Asignación rol-permiso (PK compuesta).
CREATE TABLE rol_permisos (
    rol_id     INT NOT NULL REFERENCES roles(id)    ON DELETE RESTRICT,
    permiso_id INT NOT NULL REFERENCES permisos(id) ON DELETE RESTRICT,
    PRIMARY KEY (rol_id, permiso_id)
);

-- Usuarios del sistema. Borrado LÓGICO: deleted_at/deleted_by (nunca DELETE físico).
CREATE TABLE usuarios (
    id                     BIGSERIAL PRIMARY KEY,
    username               VARCHAR(30)  NOT NULL UNIQUE,  -- alias, ej. 'vendedor1'
    nombre                 VARCHAR(100) NOT NULL,          -- nombre para mostrar
    password_hash          VARCHAR(100) NOT NULL,          -- bcrypt (cost 12)
    rol_id                 INT          NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    activo                 BOOLEAN      NOT NULL DEFAULT TRUE,
    debe_cambiar_password  BOOLEAN      NOT NULL DEFAULT FALSE,
    intentos_fallidos      INT          NOT NULL DEFAULT 0,
    bloqueado_hasta        TIMESTAMPTZ,                    -- bloqueo temporal por intentos
    ultimo_acceso          TIMESTAMPTZ,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at             TIMESTAMPTZ,                    -- borrado lógico
    deleted_by             BIGINT
);
CREATE INDEX ix_usuarios_username ON usuarios (username);

-- Sesiones (refresh tokens). Solo se guarda el hash SHA-256 del token.
CREATE TABLE sesiones (
    id                 BIGSERIAL PRIMARY KEY,
    usuario_id         BIGINT      NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
    ip                 VARCHAR(45)  NOT NULL DEFAULT '',
    user_agent         VARCHAR(400) NOT NULL DEFAULT '',
    expira_en          TIMESTAMPTZ NOT NULL,   -- TTL según rol (configurable en BD)
    revocada           BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_sesiones_usuario_id ON sesiones (usuario_id);

-- Bitácora de auditoría: quién hizo qué. INMUTABLE (ver trigger más abajo).
CREATE TABLE bitacora_auditoria (
    id             BIGSERIAL PRIMARY KEY,
    usuario_id     BIGINT REFERENCES usuarios(id) ON DELETE RESTRICT,  -- NULL si login de user inexistente
    rol            VARCHAR(30)  NOT NULL DEFAULT '',
    accion         VARCHAR(60)  NOT NULL,   -- ej. 'login_fallido', 'venta_registrada'
    entidad        VARCHAR(60)  NOT NULL,   -- ej. 'usuarios', 'ventas', 'productos'
    entidad_id     VARCHAR(60),
    valor_anterior JSONB,                    -- estado antes del cambio
    valor_nuevo    JSONB,                    -- estado después del cambio
    motivo         TEXT,
    ip             VARCHAR(45)  NOT NULL DEFAULT '',
    user_agent     VARCHAR(400) NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_bitacora_created_at  ON bitacora_auditoria (created_at);
CREATE INDEX ix_bitacora_usuario_id  ON bitacora_auditoria (usuario_id);
CREATE INDEX ix_bitacora_entidad     ON bitacora_auditoria (entidad);

-- Configuración e identidad visual (fila única id=1). Solo ADMIN la edita.
CREATE TABLE configuracion_negocio (
    id                         INT PRIMARY KEY,               -- siempre 1
    nombre_negocio             VARCHAR(120) NOT NULL DEFAULT 'Mi Tienda',
    logo_url                   TEXT         NOT NULL DEFAULT '',   -- URL o data-URI base64
    color_primario             VARCHAR(20)  NOT NULL DEFAULT '#2563eb',
    color_secundario           VARCHAR(20)  NOT NULL DEFAULT '#f59e0b',
    tipografia                 VARCHAR(60)  NOT NULL DEFAULT 'Inter',
    session_ttl_admin_minutos  INT          NOT NULL DEFAULT 43200,  -- 30 días
    session_ttl_cajero_minutos INT          NOT NULL DEFAULT 720,    -- 12 horas
    max_intentos_login         INT          NOT NULL DEFAULT 3,
    minutos_bloqueo            INT          NOT NULL DEFAULT 15,
    updated_by                 BIGINT REFERENCES usuarios(id) ON DELETE RESTRICT,
    updated_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 3. Inmutabilidad de la bitácora (defensa en dos capas)
-- ---------------------------------------------------------------------------
-- Capa 1: trigger que rechaza cualquier UPDATE/DELETE, venga de quien venga.
CREATE OR REPLACE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La bitácora de auditoría es inmutable: no se permite % sobre ella', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bitacora_inmutable
BEFORE UPDATE OR DELETE ON bitacora_auditoria
FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable();

-- ---------------------------------------------------------------------------
-- 4. Privilegios (capa 2 de la inmutabilidad + mínimo privilegio)
-- ---------------------------------------------------------------------------
-- App: CRUD normal sobre sus tablas...
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_kiosko;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_kiosko;
-- ...pero SIN UPDATE/DELETE sobre la bitácora (solo insertar y leer):
REVOKE UPDATE, DELETE ON bitacora_auditoria FROM app_kiosko;

-- pgAdmin de consulta: solo lectura de todo.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lectura_pgadmin;

-- ---------------------------------------------------------------------------
-- 5. Seed mínimo (la versión completa y parametrizada es backend/scripts/seed.py)
-- ---------------------------------------------------------------------------
INSERT INTO roles (nombre, descripcion) VALUES
    ('ADMIN',  'Dueña de la tienda: control total del sistema.'),
    ('CAJERO', 'Vendedor: permisos limitados a la operación diaria.');

INSERT INTO permisos (codigo, descripcion) VALUES
    ('usuarios.gestionar',          'Crear, editar y desactivar usuarios'),
    ('productos.crear',             'Crear productos en el catálogo'),
    ('productos.editar',            'Editar productos del catálogo'),
    ('precios.editar',              'Modificar precios'),
    ('inventario.aprobar_ingreso',  'Aprobar ingresos de mercadería'),
    ('inventario.solicitar_ingreso','Solicitar/registrar ingresos de mercadería'),
    ('inventario.ver',              'Consultar inventario y stock'),
    ('ventas.registrar',            'Registrar ventas en el POS'),
    ('ventas.anular',               'Anular ventas'),
    ('caja.abrir_turno',            'Abrir turno de caja'),
    ('caja.cerrar_turno',           'Cerrar turno de caja'),
    ('reportes.ver',                'Ver reportes'),
    ('registros.eliminar',          'Borrado lógico de registros'),
    ('bitacora.ver',                'Consultar la bitácora de auditoría'),
    ('configuracion.editar',        'Editar configuración e identidad visual');

-- ADMIN: todos los permisos. CAJERO: solo los operativos.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permisos p WHERE r.nombre = 'ADMIN';

INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r JOIN permisos p ON p.codigo IN (
    'inventario.solicitar_ingreso', 'inventario.ver', 'ventas.registrar',
    'caja.abrir_turno', 'caja.cerrar_turno'
) WHERE r.nombre = 'CAJERO';

INSERT INTO configuracion_negocio (id) VALUES (1);

-- El usuario ADMIN inicial se crea con backend/scripts/seed.py
-- (la contraseña viene de la variable de entorno ADMIN_PASSWORD, nunca de un .sql).
