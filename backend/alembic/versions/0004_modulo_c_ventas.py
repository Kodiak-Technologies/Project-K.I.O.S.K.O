"""Módulo C — HU-C01: ventas y sus detalles (snapshot de nombre y precio).

Revision ID: 0004_modulo_c_ventas
Revises: 0003_modulo_c_turnos
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_modulo_c_ventas"
down_revision = "0003_modulo_c_turnos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ventas",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("turno_id", sa.BigInteger, sa.ForeignKey("turnos_caja.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vendedor", sa.String(100), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("metodo_pago", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="COMPLETADA"),
        sa.Column("motivo_anulacion", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ventas_created_at", "ventas", ["created_at"])
    op.create_index("ix_ventas_turno_id", "ventas", ["turno_id"])

    op.create_table(
        "detalles_venta",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("venta_id", sa.BigInteger, sa.ForeignKey("ventas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("producto_id", sa.BigInteger, sa.ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("cantidad", sa.Integer, nullable=False),
        sa.Column("cantidad_devuelta", sa.Integer, nullable=False, server_default="0"),
        sa.CheckConstraint("cantidad > 0", name="ck_detalles_cantidad_positiva"),
    )
    op.create_index("ix_detalles_venta_venta_id", "detalles_venta", ["venta_id"])


def downgrade() -> None:
    op.drop_table("detalles_venta")
    op.drop_table("ventas")
