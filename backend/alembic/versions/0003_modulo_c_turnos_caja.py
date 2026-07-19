"""Módulo C — HU-C06: turnos de caja (apertura manual con monto inicial).

Revision ID: 0003_modulo_c_turnos
Revises: 0002_modulo_b_min
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_modulo_c_turnos"
down_revision = "0002_modulo_b_min"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # La rama del módulo D creó una versión placeholder de turnos_caja (con enum
    # estado_caja) para probar sus boletas. Si existe, se reemplaza por la definitiva:
    # se detecta porque su columna estado es un enum (USER-DEFINED) y no VARCHAR.
    op.execute(
        """
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
        """
    )

    op.create_table(
        "turnos_caja",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("abierto_por", sa.String(100), nullable=False),
        sa.Column("monto_inicial", sa.Numeric(10, 2), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="ABIERTO"),
        sa.Column("abierto_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cerrado_en", sa.DateTime(timezone=True)),
        sa.Column("monto_final", sa.Numeric(10, 2)),
        sa.Column("usuario_cierre_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT")),
        sa.Column("cerrado_por", sa.String(100)),
        sa.CheckConstraint("monto_inicial >= 0", name="ck_turnos_monto_inicial_no_negativo"),
    )
    # Una sola caja física: no puede haber dos turnos ABIERTOs a la vez.
    op.create_index(
        "ux_turnos_caja_abierto",
        "turnos_caja",
        ["estado"],
        unique=True,
        postgresql_where=sa.text("estado = 'ABIERTO'"),
    )


def downgrade() -> None:
    op.drop_index("ux_turnos_caja_abierto", table_name="turnos_caja")
    op.drop_table("turnos_caja")
