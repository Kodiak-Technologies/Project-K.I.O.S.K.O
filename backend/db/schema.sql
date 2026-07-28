-- =============================================================================
-- PROJECT K.I.O.S.K.O — ESQUEMA DEFINITIVO
-- PostgreSQL 16
-- =============================================================================
--
-- Este archivo es la ÚNICA fuente de verdad del esquema. Reemplaza a los
-- cuatro `schema_modulo_*.sql` anteriores, que se habían desincronizado entre
-- sí y con el código.
--
-- Se genera desde los modelos SQLAlchemy (lo que la aplicación realmente
-- mapea), así que no puede haber columnas que el código no use ni columnas que
-- el código espere y no existan.
--
-- CÓMO USARLO
--   Sobre una base vacía:   psql "$DATABASE_URL" -f db/schema.sql
--   Para recrear desde cero: descomentar el bloque "RESET" de abajo.
--
-- QUÉ SE LIMPIÓ RESPECTO DE LA BD ANTERIOR
--   * Tabla `mermas` (22 columnas, 6 FKs, 4 índices): el flujo se eliminó y su
--     reemplazo es el ajuste manual de stock. Con ella se van
--     `movimientos_inventario.merma_id` y el tipo de movimiento 'merma'.
--   * `productos.foto_url`: los productos ya no llevan foto.
--   * 5 permisos huérfanos: `mermas.registrar`, `mermas.confirmar` y los tres
--     del fiado (`clientes.gestionar`, `clientes.limite_credito`,
--     `fiados.abonar`), que sobrevivían a features ya eliminadas.
--
-- DECISIONES DE DISEÑO QUE CONVIENE CONOCER
--   * Borrado lógico (`deleted_at`/`deleted_by`) en las entidades de negocio.
--     El histórico contable nunca se borra: las FKs son ON DELETE RESTRICT.
--   * Snapshots de nombre (`*_por_nombre`) junto a cada FK de usuario. Es
--     denormalización deliberada: el histórico tiene que poder leerse aunque
--     el usuario se renombre o se dé de baja.
--   * Unicidad PARCIAL (`WHERE deleted_at IS NULL`) en los identificadores de
--     negocio: al dar de baja un producto, su código queda libre para reusar.
--   * `bitacora_auditoria` e `historial_precios` son inmutables por trigger:
--     solo aceptan INSERT.
-- =============================================================================


-- =============================================================================
-- RESET — descomentar SOLO si querés borrar todo y empezar de cero.
-- =============================================================================
-- DROP SCHEMA public CASCADE;
-- CREATE SCHEMA public;


-- =============================================================================
-- MÓDULO A — Seguridad (usuarios, roles, permisos, sesiones, auditoría)
-- =============================================================================

CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(30)  NOT NULL UNIQUE,
    descripcion VARCHAR(255) NOT NULL
);

CREATE TABLE permisos (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(60)  NOT NULL UNIQUE,
    descripcion VARCHAR(255) NOT NULL
);

CREATE TABLE rol_permisos (
    rol_id     INTEGER NOT NULL REFERENCES roles (id)    ON DELETE RESTRICT,
    permiso_id INTEGER NOT NULL REFERENCES permisos (id) ON DELETE RESTRICT,
    PRIMARY KEY (rol_id, permiso_id)
);

CREATE TABLE usuarios (
    id                    BIGSERIAL PRIMARY KEY,
    username              VARCHAR(30)  NOT NULL UNIQUE,
    nombre                VARCHAR(100) NOT NULL,
    password_hash         VARCHAR(100) NOT NULL,
    rol_id                INTEGER      NOT NULL REFERENCES roles (id) ON DELETE RESTRICT,
    activo                BOOLEAN      NOT NULL DEFAULT TRUE,
    debe_cambiar_password BOOLEAN      NOT NULL DEFAULT FALSE,
    intentos_fallidos     INTEGER      NOT NULL DEFAULT 0,
    bloqueado_hasta       TIMESTAMPTZ,
    ultimo_acceso         TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ,
    -- FK agregada: antes era un entero suelto y podía apuntar a nadie.
    deleted_by            BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT
);
-- El UNIQUE de `username` ya crea su índice: no hace falta otro.

CREATE TABLE sesiones (
    id                 BIGSERIAL PRIMARY KEY,
    usuario_id         BIGINT       NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
    refresh_token_hash VARCHAR(64)  NOT NULL UNIQUE,
    ip                 VARCHAR(45)  NOT NULL DEFAULT '',
    user_agent         VARCHAR(400) NOT NULL DEFAULT '',
    expira_en          TIMESTAMPTZ  NOT NULL,
    revocada           BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_sesiones_usuario_id ON sesiones (usuario_id);

CREATE TABLE bitacora_auditoria (
    id             BIGSERIAL PRIMARY KEY,
    usuario_id     BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    rol            VARCHAR(30)  NOT NULL DEFAULT '',
    accion         VARCHAR(60)  NOT NULL,
    entidad        VARCHAR(60)  NOT NULL,
    entidad_id     VARCHAR(60),
    valor_anterior JSONB,
    valor_nuevo    JSONB,
    motivo         TEXT,
    ip             VARCHAR(45)  NOT NULL DEFAULT '',
    user_agent     VARCHAR(400) NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_bitacora_usuario_id ON bitacora_auditoria (usuario_id);
CREATE INDEX ix_bitacora_entidad    ON bitacora_auditoria (entidad);
-- Compuesto y en el mismo sentido que el ORDER BY del listado: la paginación
-- por cursor hace `WHERE (created_at, id) < (:f, :id)` y salta directo acá.
CREATE INDEX ix_bitacora_created_at_id ON bitacora_auditoria (created_at DESC, id DESC);

CREATE TABLE configuracion_negocio (
    id                         SERIAL PRIMARY KEY,
    nombre_negocio             VARCHAR(120) NOT NULL DEFAULT 'Mi Tienda',
    logo_url                   TEXT         NOT NULL DEFAULT '',
    color_primario             VARCHAR(20)  NOT NULL DEFAULT '#2563eb',
    color_secundario           VARCHAR(20)  NOT NULL DEFAULT '#f59e0b',
    tipografia                 VARCHAR(60)  NOT NULL DEFAULT 'Inter',
    session_ttl_admin_minutos  INTEGER      NOT NULL DEFAULT 43200,
    session_ttl_cajero_minutos INTEGER      NOT NULL DEFAULT 720,
    max_intentos_login         INTEGER      NOT NULL DEFAULT 3,
    minutos_bloqueo            INTEGER      NOT NULL DEFAULT 15,
    updated_by                 BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    updated_at                 TIMESTAMPTZ  NOT NULL DEFAULT now()
);


-- =============================================================================
-- MÓDULO B — Inventario (catálogo, proveedores, ingresos, movimientos)
-- =============================================================================

CREATE TABLE categorias (
    id                SERIAL PRIMARY KEY,
    nombre            VARCHAR(80) NOT NULL,
    descripcion       TEXT,
    creado_por        BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    creado_por_nombre VARCHAR(100),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    deleted_by        BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT
);
-- Único PARCIAL: una categoría dada de baja libera su nombre.
CREATE UNIQUE INDEX uq_categorias_nombre ON categorias (nombre) WHERE deleted_at IS NULL;

CREATE TABLE proveedores (
    id                BIGSERIAL PRIMARY KEY,
    razon_social      VARCHAR(120)  NOT NULL,
    ruc               VARCHAR(20),
    telefono          VARCHAR(20),
    email             VARCHAR(120),
    direccion         TEXT,
    activo            BOOLEAN       NOT NULL DEFAULT TRUE,
    deuda_actual      NUMERIC(12,2) NOT NULL DEFAULT 0,
    creado_por        BIGINT        NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
    creado_por_nombre VARCHAR(100)  NOT NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    deleted_by        BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT ck_proveedores_deuda_no_negativa CHECK (deuda_actual >= 0)
);
CREATE UNIQUE INDEX uq_proveedores_ruc ON proveedores (ruc)
    WHERE ruc IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_proveedores_razon  ON proveedores (lower(razon_social)) WHERE deleted_at IS NULL;
CREATE INDEX idx_proveedores_activo ON proveedores (activo)             WHERE deleted_at IS NULL;

CREATE TABLE productos (
    id                      BIGSERIAL PRIMARY KEY,
    codigo                  VARCHAR(60)   NOT NULL,
    nombre                  VARCHAR(150)  NOT NULL,
    categoria_id            INTEGER REFERENCES categorias (id) ON DELETE RESTRICT,
    precio                  NUMERIC(10,2) NOT NULL,
    precio_compra_actual    NUMERIC(10,2) NOT NULL DEFAULT 0,
    es_codigo_interno       BOOLEAN       NOT NULL DEFAULT FALSE,
    alerta_stock_notificada BOOLEAN       NOT NULL DEFAULT FALSE,
    stock                   INTEGER       NOT NULL DEFAULT 0,
    stock_minimo            INTEGER       NOT NULL DEFAULT 0,
    activo                  BOOLEAN       NOT NULL DEFAULT TRUE,
    creado_por              BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    creado_por_nombre       VARCHAR(100),
    actualizado_por         BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    actualizado_por_nombre  VARCHAR(100),
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at              TIMESTAMPTZ,
    deleted_by              BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT ck_productos_stock_no_negativo        CHECK (stock >= 0),
    CONSTRAINT ck_productos_precio_compra_no_negativo CHECK (precio_compra_actual >= 0)
);
-- Único PARCIAL: dar de baja un producto libera su código de barras para
-- volver a usarlo (mismo criterio que `proveedores.ruc`). El histórico no se
-- vuelve ambiguo porque apunta a `producto_id`, no al código.
CREATE UNIQUE INDEX uq_productos_codigo ON productos (codigo) WHERE deleted_at IS NULL;
CREATE INDEX ix_productos_nombre  ON productos (nombre);
CREATE INDEX idx_productos_nombre_lower ON productos (lower(nombre))  WHERE deleted_at IS NULL;
CREATE INDEX idx_productos_activo_stock ON productos (activo, stock)  WHERE deleted_at IS NULL;

CREATE TABLE solicitudes_ingreso (
    id                    BIGSERIAL PRIMARY KEY,
    proveedor_id          BIGINT REFERENCES proveedores (id) ON DELETE RESTRICT,
    estado                VARCHAR(20)  NOT NULL DEFAULT 'Pendiente',
    foto_boleta_url       TEXT         NOT NULL,
    motivo                TEXT,
    motivo_rechazo        TEXT,
    solicitado_por        BIGINT       NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
    solicitado_por_nombre VARCHAR(100) NOT NULL,
    revisado_por          BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    revisado_por_nombre   VARCHAR(100),
    revisado_en           TIMESTAMPTZ,
    editado_por           BIGINT REFERENCES usuarios (id) ON DELETE SET NULL,
    editado_por_nombre    VARCHAR(100),
    editado_en            TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ,
    deleted_by            BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT chk_solicitudes_estado CHECK (estado IN ('Pendiente','Aprobada','Rechazada')),
    CONSTRAINT chk_solicitudes_rechazo_tiene_motivo CHECK (
        (estado = 'Rechazada' AND motivo_rechazo IS NOT NULL
         AND length(trim(motivo_rechazo)) > 0)
        OR estado <> 'Rechazada'
    ),
    CONSTRAINT chk_solicitudes_revisado_consistente CHECK (
        (estado = 'Pendiente' AND revisado_por IS NULL AND revisado_en IS NULL)
        OR (estado IN ('Aprobada','Rechazada')
            AND revisado_por IS NOT NULL AND revisado_en IS NOT NULL)
    )
);
CREATE INDEX idx_solicitudes_estado      ON solicitudes_ingreso (estado, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_solicitudes_proveedor   ON solicitudes_ingreso (proveedor_id)            WHERE deleted_at IS NULL;
CREATE INDEX idx_solicitudes_solicitante ON solicitudes_ingreso (solicitado_por, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_solicitudes_editado_en  ON solicitudes_ingreso (editado_en DESC)
    WHERE editado_en IS NOT NULL AND deleted_at IS NULL;
-- Para la paginación por cursor del listado general.
CREATE INDEX idx_solicitudes_created_at_id ON solicitudes_ingreso (created_at DESC, id DESC)
    WHERE deleted_at IS NULL;

CREATE TABLE detalle_solicitud (
    id                     BIGSERIAL PRIMARY KEY,
    solicitud_id           BIGINT        NOT NULL REFERENCES solicitudes_ingreso (id) ON DELETE CASCADE,
    producto_id            BIGINT        NOT NULL REFERENCES productos (id)           ON DELETE RESTRICT,
    cantidad               INTEGER       NOT NULL,
    precio_compra_unitario NUMERIC(10,2) NOT NULL,
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT chk_detsol_cantidad_positiva  CHECK (cantidad > 0),
    CONSTRAINT chk_detsol_precio_no_negativo CHECK (precio_compra_unitario >= 0)
);
CREATE INDEX idx_detsol_solicitud ON detalle_solicitud (solicitud_id);
CREATE INDEX idx_detsol_producto  ON detalle_solicitud (producto_id);

CREATE TABLE pagos_proveedor (
    id                    BIGSERIAL PRIMARY KEY,
    proveedor_id          BIGINT        NOT NULL REFERENCES proveedores (id) ON DELETE RESTRICT,
    tipo                  VARCHAR(20)   NOT NULL,
    monto                 NUMERIC(12,2) NOT NULL,
    concepto              TEXT,
    fecha                 DATE          NOT NULL,
    solicitud_ingreso_id  BIGINT REFERENCES solicitudes_ingreso (id) ON DELETE RESTRICT,
    registrado_por        BIGINT        NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
    registrado_por_nombre VARCHAR(100)  NOT NULL,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ,
    deleted_by            BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT chk_pagos_monto_positivo CHECK (monto > 0),
    CONSTRAINT chk_pagos_tipo           CHECK (tipo IN ('compra_credito','pago')),
    -- Solo una compra a crédito puede colgar de una solicitud de ingreso.
    CONSTRAINT chk_pagos_solicitud_solo_en_compra CHECK (
        tipo = 'compra_credito' OR solicitud_ingreso_id IS NULL
    )
);
CREATE INDEX idx_pagos_proveedor ON pagos_proveedor (proveedor_id, fecha DESC);
CREATE INDEX idx_pagos_tipo      ON pagos_proveedor (tipo);

-- Bitácora append-only de TODA variación de stock (D-07).
CREATE TABLE movimientos_inventario (
    id                    BIGSERIAL PRIMARY KEY,
    producto_id           BIGINT       NOT NULL REFERENCES productos (id) ON DELETE RESTRICT,
    cantidad              INTEGER      NOT NULL,
    tipo                  VARCHAR(20)  NOT NULL,
    motivo                VARCHAR(200),
    solicitud_ingreso_id  BIGINT REFERENCES solicitudes_ingreso (id) ON DELETE RESTRICT,
    registrado_por        BIGINT       NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
    registrado_por_nombre VARCHAR(100) NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT chk_mov_cantidad_no_cero CHECK (cantidad <> 0),
    CONSTRAINT chk_mov_tipo CHECK (tipo IN ('ingreso','ajuste','venta','devolucion')),
    -- El signo lo dicta el tipo; el ajuste manual puede ir en cualquiera.
    CONSTRAINT chk_mov_signo_por_tipo CHECK (
        (tipo IN ('ingreso','devolucion') AND cantidad > 0)
        OR (tipo = 'venta' AND cantidad < 0)
        OR (tipo = 'ajuste')
    ),
    CONSTRAINT chk_mov_ingreso_tiene_solicitud CHECK (
        tipo <> 'ingreso' OR solicitud_ingreso_id IS NOT NULL
    ),
    -- El ajuste manual siempre lleva motivo: es la trazabilidad del faltante.
    CONSTRAINT chk_mov_ajuste_tiene_motivo CHECK (
        tipo <> 'ajuste' OR (motivo IS NOT NULL AND length(trim(motivo)) > 0)
    )
);
CREATE INDEX idx_mov_producto_fecha ON movimientos_inventario (producto_id, created_at DESC);
CREATE INDEX idx_mov_tipo           ON movimientos_inventario (tipo);
CREATE INDEX idx_mov_solicitud      ON movimientos_inventario (solicitud_ingreso_id)
    WHERE solicitud_ingreso_id IS NOT NULL;
-- Para la paginación por cursor del listado.
CREATE INDEX idx_mov_created_at_id  ON movimientos_inventario (created_at DESC, id DESC);

CREATE TABLE historial_precios (
    id                    BIGSERIAL PRIMARY KEY,
    producto_id           BIGINT        NOT NULL REFERENCES productos (id) ON DELETE RESTRICT,
    precio_anterior       NUMERIC(10,2),
    precio_nuevo          NUMERIC(10,2) NOT NULL,
    tipo_precio           VARCHAR(20)   NOT NULL,
    modificado_por        BIGINT        NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
    modificado_por_nombre VARCHAR(100)  NOT NULL,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT chk_historial_precio_no_negativo CHECK (precio_nuevo >= 0),
    CONSTRAINT chk_historial_tipo               CHECK (tipo_precio IN ('venta','compra'))
);
CREATE INDEX idx_historial_producto_fecha ON historial_precios (producto_id, tipo_precio, created_at DESC);
CREATE INDEX idx_historial_created_at_id  ON historial_precios (created_at DESC, id DESC);


-- =============================================================================
-- MÓDULO C — Ventas y caja
-- =============================================================================

CREATE TABLE metodos_pago (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(20) NOT NULL UNIQUE,
    nombre      VARCHAR(50) NOT NULL,
    es_efectivo BOOLEAN     NOT NULL DEFAULT FALSE,
    activo      BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE TABLE turnos_caja (
    id                BIGSERIAL PRIMARY KEY,
    usuario_id        BIGINT        NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
    abierto_por       VARCHAR(100)  NOT NULL,
    monto_inicial     NUMERIC(10,2) NOT NULL,
    estado            VARCHAR(10)   NOT NULL,
    abierto_en        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    cerrado_en        TIMESTAMPTZ,
    monto_final       NUMERIC(10,2),
    usuario_cierre_id BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    cerrado_por       VARCHAR(100),
    asignado_a_id     BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT ck_turnos_monto_inicial_no_negativo CHECK (monto_inicial >= 0)
);
-- Un solo turno abierto a la vez en todo el sistema.
CREATE UNIQUE INDEX ux_turnos_caja_abierto ON turnos_caja (estado) WHERE estado = 'ABIERTO';

CREATE TABLE arqueos (
    id                 BIGSERIAL PRIMARY KEY,
    turno_id           BIGINT        NOT NULL UNIQUE REFERENCES turnos_caja (id) ON DELETE RESTRICT,
    usuario_id         BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
    cerrado_por        VARCHAR(100)  NOT NULL,
    efectivo_esperado  NUMERIC(10,2) NOT NULL,
    efectivo_contado   NUMERIC(10,2) NOT NULL,
    diferencia         NUMERIC(10,2) NOT NULL,
    comentario         TEXT,
    total_vendido      NUMERIC(10,2) NOT NULL DEFAULT 0,
    totales_por_metodo JSONB,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE ventas (
    id                 BIGSERIAL PRIMARY KEY,
    turno_id           BIGINT        NOT NULL REFERENCES turnos_caja (id) ON DELETE RESTRICT,
    usuario_id         BIGINT        NOT NULL REFERENCES usuarios (id)    ON DELETE RESTRICT,
    vendedor           VARCHAR(100)  NOT NULL,
    total              NUMERIC(10,2) NOT NULL,
    -- Resumen: dice 'MIXTO' si se pagó con más de un método. El desglose real
    -- vive en `pagos_venta`, que es de donde salen los reportes.
    metodo_pago        VARCHAR(20)   NOT NULL,
    estado             VARCHAR(20)   NOT NULL DEFAULT 'COMPLETADA',
    motivo_anulacion   TEXT,
    -- Idempotencia de la venta offline: el cliente manda su propio UUID.
    client_uuid        VARCHAR(36) UNIQUE,
    registrada_offline BOOLEAN       NOT NULL DEFAULT FALSE,
    vendida_en         TIMESTAMPTZ,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_ventas_turno_id   ON ventas (turno_id);
CREATE INDEX ix_ventas_created_at ON ventas (created_at DESC);

CREATE TABLE detalles_venta (
    id                BIGSERIAL PRIMARY KEY,
    venta_id          BIGINT        NOT NULL REFERENCES ventas (id)    ON DELETE RESTRICT,
    producto_id       BIGINT        NOT NULL REFERENCES productos (id) ON DELETE RESTRICT,
    -- Snapshot: el ticket tiene que poder reimprimirse aunque el producto
    -- cambie de nombre o de precio después.
    nombre            VARCHAR(150)  NOT NULL,
    precio_unitario   NUMERIC(10,2) NOT NULL,
    cantidad          INTEGER       NOT NULL,
    cantidad_devuelta INTEGER       NOT NULL DEFAULT 0,
    CONSTRAINT ck_detalles_cantidad_positiva CHECK (cantidad > 0),
    CONSTRAINT ck_detalles_devuelta_valida   CHECK (cantidad_devuelta BETWEEN 0 AND cantidad)
);
CREATE INDEX ix_detalles_venta_venta_id ON detalles_venta (venta_id);
-- Los reportes agrupan por producto: sin esto era un scan de toda la tabla.
CREATE INDEX ix_detalles_venta_producto_id ON detalles_venta (producto_id);

CREATE TABLE pagos_venta (
    id             BIGSERIAL PRIMARY KEY,
    venta_id       BIGINT        NOT NULL REFERENCES ventas (id)       ON DELETE RESTRICT,
    metodo_pago_id INTEGER       NOT NULL REFERENCES metodos_pago (id) ON DELETE RESTRICT,
    -- Snapshot del método al momento de cobrar.
    codigo_metodo  VARCHAR(20)   NOT NULL,
    es_efectivo    BOOLEAN       NOT NULL,
    monto          NUMERIC(10,2) NOT NULL,
    monto_recibido NUMERIC(10,2),
    CONSTRAINT ck_pagos_monto_positivo CHECK (monto > 0)
);
CREATE INDEX ix_pagos_venta_venta_id ON pagos_venta (venta_id);

CREATE TABLE anulaciones (
    id                BIGSERIAL PRIMARY KEY,
    venta_id          BIGINT        NOT NULL REFERENCES ventas (id)      ON DELETE RESTRICT,
    turno_id          BIGINT        NOT NULL REFERENCES turnos_caja (id) ON DELETE RESTRICT,
    tipo              VARCHAR(15)   NOT NULL,
    usuario_id        BIGINT        NOT NULL REFERENCES usuarios (id)    ON DELETE RESTRICT,
    realizado_por     VARCHAR(100)  NOT NULL,
    motivo            TEXT          NOT NULL,
    monto             NUMERIC(10,2) NOT NULL,
    efectivo_devuelto NUMERIC(10,2) NOT NULL DEFAULT 0,
    items             JSONB,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_anulaciones_venta_id ON anulaciones (venta_id);
CREATE INDEX ix_anulaciones_turno_id ON anulaciones (turno_id);


-- =============================================================================
-- MÓDULO D — Documentos, notificaciones y respaldos
-- =============================================================================

CREATE TABLE notificaciones (
    id             BIGSERIAL PRIMARY KEY,
    tipo           VARCHAR(30)  NOT NULL,
    titulo         VARCHAR(120) NOT NULL,
    mensaje        TEXT         NOT NULL,
    leida          BOOLEAN      NOT NULL DEFAULT FALSE,
    entidad_origen VARCHAR(60),
    entidad_id     VARCHAR(60),
    -- usuario_id NULL = va a la administradora (bandeja general).
    usuario_id     BIGINT REFERENCES usuarios (id)  ON DELETE SET NULL,
    -- FK agregada: antes era un entero suelto.
    producto_id    BIGINT REFERENCES productos (id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_notificaciones_tipo  ON notificaciones (tipo);
-- La bandeja ordena por (leida, created_at DESC) y pagina sobre eso.
CREATE INDEX ix_notificaciones_bandeja ON notificaciones (leida, created_at DESC, id DESC);

CREATE TABLE config_notificaciones (
    id            INTEGER PRIMARY KEY DEFAULT 1,
    nivel_detalle VARCHAR(20) NOT NULL DEFAULT 'BAJO',
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Fila única: la configuración es global.
    CONSTRAINT ck_config_notif_fila_unica CHECK (id = 1)
);

CREATE TABLE respaldos (
    id             BIGSERIAL PRIMARY KEY,
    archivo_nombre VARCHAR(255) NOT NULL,
    tamano_bytes   BIGINT       NOT NULL,
    estado         VARCHAR(20)  NOT NULL,
    generado_en    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expira_en      TIMESTAMPTZ  NOT NULL,
    usuario_id     BIGINT REFERENCES usuarios (id) ON DELETE SET NULL,
    drive_file_id  VARCHAR(255)
);
CREATE INDEX ix_respaldos_usuario_id ON respaldos (usuario_id);
CREATE INDEX ix_respaldos_estado     ON respaldos (estado);
CREATE INDEX ix_respaldos_generado   ON respaldos (generado_en DESC, id DESC);

CREATE TABLE oauth_tokens (
    id                  BIGSERIAL PRIMARY KEY,
    proveedor           VARCHAR(50) NOT NULL,
    access_token        TEXT        NOT NULL,
    refresh_token       TEXT        NOT NULL,
    token_expiry        TIMESTAMPTZ,
    usuario_id          BIGINT REFERENCES usuarios (id) ON DELETE SET NULL,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_oauth_tokens_proveedor ON oauth_tokens (proveedor);


-- =============================================================================
-- INMUTABILIDAD — la auditoría y el historial de precios solo aceptan INSERT
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_solo_insert() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% es inmutable: solo se permite INSERT (intento de %)',
        TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bitacora_inmutable
    BEFORE UPDATE OR DELETE ON bitacora_auditoria
    FOR EACH ROW EXECUTE FUNCTION fn_solo_insert();

CREATE TRIGGER trg_historial_precios_no_update
    BEFORE UPDATE OR DELETE ON historial_precios
    FOR EACH ROW EXECUTE FUNCTION fn_solo_insert();


-- =============================================================================
-- SEED — lo mínimo para que el sistema arranque
-- =============================================================================

INSERT INTO roles (nombre, descripcion) VALUES
    ('ADMIN',  'Administradora del negocio: acceso total'),
    ('CAJERO', 'Cajero: ventas, caja y registro de ingresos');

INSERT INTO permisos (codigo, descripcion) VALUES
    -- Módulo A
    ('usuarios.gestionar',            'Crear, editar y desactivar usuarios'),
    ('configuracion.editar',          'Editar la configuración del negocio'),
    ('bitacora.ver',                  'Consultar la bitácora de auditoría'),
    ('registros.eliminar',            'Eliminar registros (baja lógica)'),
    -- Módulo B
    ('productos.crear',               'Crear productos en el catálogo'),
    ('productos.editar',              'Editar productos del catálogo'),
    ('precios.editar',                'Modificar precios de venta'),
    ('categorias.gestionar',          'Crear y editar categorías'),
    ('inventario.ver',                'Consultar stock y movimientos'),
    ('inventario.ajustar_stock',      'Ajustar stock manualmente'),
    ('inventario.solicitar_ingreso',  'Registrar una solicitud de ingreso'),
    ('inventario.aprobar_ingreso',    'Aprobar o rechazar ingresos'),
    ('historial_precios.ver',         'Consultar el historial de precios'),
    ('proveedores.ver',               'Consultar proveedores'),
    ('proveedores.gestionar',         'Crear y editar proveedores'),
    ('proveedores.compras_credito',   'Registrar compras a crédito'),
    ('proveedores.pagos',             'Registrar pagos a proveedores'),
    ('storage.upload',                'Subir archivos (boletas de ingreso)'),
    -- Módulo C
    ('ventas.registrar',              'Registrar ventas'),
    ('ventas.anular',                 'Anular ventas'),
    ('ventas.devolver',               'Registrar devoluciones'),
    ('caja.abrir_turno',              'Abrir turno de caja'),
    ('caja.cerrar_turno',             'Cerrar turno de caja y arquear'),
    ('metodos_pago.gestionar',        'Administrar los métodos de pago'),
    -- Módulo D
    ('reportes.ver',                  'Ver reportes y exportarlos');

-- ADMIN: todos los permisos.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permisos p WHERE r.nombre = 'ADMIN';

-- CAJERO: vender, manejar su caja, registrar ingresos y consultar inventario.
-- Anular y devolver están incluidos a propósito (HU-C08): el cajero resuelve
-- el error en el momento y queda el rastro en la bitácora. La ADMIN lo
-- supervisa desde el panel de caja y puede quitarle el permiso sin redeploy.
-- Debe coincidir con la lista de `scripts/seed.py`.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r JOIN permisos p ON p.codigo IN (
    'ventas.registrar',
    'ventas.anular',
    'ventas.devolver',
    'caja.abrir_turno',
    'caja.cerrar_turno',
    'inventario.ver',
    'inventario.solicitar_ingreso',
    'proveedores.ver',
    'storage.upload'
)
WHERE r.nombre = 'CAJERO';

-- Usuario inicial: admin / admin123 (hash bcrypt verificado contra el hasher
-- de la aplicación). Entra con `debe_cambiar_password = TRUE`, así que el
-- sistema obliga a cambiarla en el primer ingreso.
--
-- La contraseña está acá porque el esquema tiene que dejar el sistema usable.
-- Si preferís que no viaje en el repo, borrá este INSERT y creá el usuario con
-- `ADMIN_PASSWORD=... python -m scripts.seed`, que la toma del entorno.
INSERT INTO usuarios (username, nombre, password_hash, rol_id, debe_cambiar_password)
SELECT 'admin', 'Administradora',
       '$2b$12$U2hBnJY81s29hnybKNRdEOGnHGk5xUABImHjdl4obN1Mv/J7gT10u', r.id, TRUE
FROM roles r WHERE r.nombre = 'ADMIN';

INSERT INTO metodos_pago (codigo, nombre, es_efectivo, activo) VALUES
    ('EFECTIVO', 'Efectivo',       TRUE,  TRUE),
    ('YAPE',     'Yape',           FALSE, TRUE),
    ('PLIN',     'Plin',           FALSE, TRUE),
    ('TARJETA',  'Tarjeta',        FALSE, TRUE),
    ('TRANSF',   'Transferencia',  FALSE, TRUE);

INSERT INTO configuracion_negocio (nombre_negocio) VALUES ('Mi Tienda');

INSERT INTO config_notificaciones (id, nivel_detalle) VALUES (1, 'BAJO');
