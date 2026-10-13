# Esquema de fiados: se crea al arrancar el backend, de forma idempotente.
#
# ¿Por qué no Alembic? La BD compartida tiene un `alembic_version` de otra rama
# que no existe en este repo, así que `alembic upgrade` no puede correr contra
# ella (mismo motivo que backend/db/schema_modulo_c.sql). Esto SOLO crea tablas
# e índices nuevos (IF NOT EXISTS) y agrega el método FIADO INACTIVO: no altera
# ni borra nada existente. Inactivo = el catálogo normal (y el front viejo) no lo
# ofrece; este backend lo usa por código.
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

SENTENCIAS = [
    # Dos instancias arrancando a la vez no deben pisarse.
    "SELECT pg_advisory_xact_lock(724100501)",
    """
    CREATE TABLE IF NOT EXISTS clientes_fiado (
        id             BIGSERIAL PRIMARY KEY,
        nombre         VARCHAR(120)  NOT NULL,
        telefono       VARCHAR(30),
        nota           VARCHAR(300),
        limite_mensual NUMERIC(10,2) NOT NULL DEFAULT 0
                       CONSTRAINT ck_clientes_fiado_limite_no_negativo CHECK (limite_mensual >= 0),
        saldo          NUMERIC(10,2) NOT NULL DEFAULT 0,
        activo         BOOLEAN       NOT NULL DEFAULT TRUE,
        creado_por     BIGINT REFERENCES usuarios (id) ON DELETE RESTRICT,
        created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
        updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_clientes_fiado_nombre ON clientes_fiado (lower(nombre))",
    """
    CREATE TABLE IF NOT EXISTS movimientos_fiado (
        id               BIGSERIAL PRIMARY KEY,
        cliente_id       BIGINT        NOT NULL REFERENCES clientes_fiado (id) ON DELETE RESTRICT,
        tipo             VARCHAR(20)   NOT NULL
                         CONSTRAINT ck_movimientos_fiado_tipo
                         CHECK (tipo IN ('CONSUMO','PAGO','ADELANTO','REVERSO')),
        monto            NUMERIC(10,2) NOT NULL
                         CONSTRAINT ck_movimientos_fiado_monto_positivo CHECK (monto > 0),
        saldo_resultante NUMERIC(10,2) NOT NULL,
        venta_id         BIGINT  REFERENCES ventas (id) ON DELETE RESTRICT,
        anulacion_id     BIGINT  REFERENCES anulaciones (id) ON DELETE RESTRICT,
        turno_id         BIGINT  REFERENCES turnos_caja (id) ON DELETE RESTRICT,
        metodo_pago_id   INTEGER REFERENCES metodos_pago (id) ON DELETE RESTRICT,
        codigo_metodo    VARCHAR(20),
        es_efectivo      BOOLEAN       NOT NULL DEFAULT FALSE,
        entra_a_caja     BOOLEAN       NOT NULL DEFAULT FALSE,
        nota             VARCHAR(300),
        usuario_id       BIGINT        NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
        registrado_por   VARCHAR(100)  NOT NULL,
        created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_movimientos_fiado_cliente ON movimientos_fiado (cliente_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_movimientos_fiado_turno ON movimientos_fiado (turno_id)",
    "CREATE INDEX IF NOT EXISTS ix_movimientos_fiado_venta ON movimientos_fiado (venta_id)",
    # NOT EXISTS y no ON CONFLICT: no depende de que la BD tenga el UNIQUE en codigo.
    """
    INSERT INTO metodos_pago (codigo, nombre, es_efectivo, activo)
    SELECT 'FIADO', 'Fiado', FALSE, FALSE
    WHERE NOT EXISTS (SELECT 1 FROM metodos_pago WHERE codigo = 'FIADO')
    """,
]


async def asegurar_esquema_fiados(engine: AsyncEngine) -> None:
    """Crea lo que falte. Si falla, el resto del sistema sigue funcionando."""
    try:
        async with engine.begin() as conn:
            for sentencia in SENTENCIAS:
                await conn.execute(text(sentencia))
        logger.info("Esquema de fiados verificado.")
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo crear el esquema de fiados: %s", exc, exc_info=True)
