"""Módulo C — HU-C08: anulaciones y devoluciones (el rastro de los reversos).

Revision ID: 0007_modulo_c_anulaciones
Revises: 0006_modulo_c_arqueos
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_modulo_c_anulaciones"
down_revision = "0006_modulo_c_arqueos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anulaciones",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("venta_id", sa.BigInteger, sa.ForeignKey("ventas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("turno_id", sa.BigInteger, sa.ForeignKey("turnos_caja.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo", sa.String(15), nullable=False),  # ANULACION | DEVOLUCION
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("realizado_por", sa.String(100), nullable=False),
        sa.Column("motivo", sa.Text, nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("efectivo_devuelto", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("items", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_anulaciones_venta_id", "anulaciones", ["venta_id"])
    op.create_index("ix_anulaciones_turno_id", "anulaciones", ["turno_id"])


def downgrade() -> None:
    op.drop_table("anulaciones")
