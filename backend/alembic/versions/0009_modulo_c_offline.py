"""Módulo C — HU-C10: campos para el modo offline con sincronización (RF-26).

Revision ID: 0009_modulo_c_offline
Revises: 0008_modulo_c_fiados
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_modulo_c_offline"
down_revision = "0008_modulo_c_fiados"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # client_uuid: generado por el POS al vender sin internet; UNIQUE garantiza
    # que reintentar la sincronización nunca duplique la venta (idempotencia).
    op.add_column("ventas", sa.Column("client_uuid", sa.String(36), unique=True))
    op.add_column(
        "ventas",
        sa.Column("registrada_offline", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    # Momento REAL de la venta (offline: anterior a created_at, que es la sincronización).
    op.add_column("ventas", sa.Column("vendida_en", sa.DateTime(timezone=True)))
    op.create_index("ux_ventas_client_uuid", "ventas", ["client_uuid"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_ventas_client_uuid", table_name="ventas")
    op.drop_column("ventas", "vendida_en")
    op.drop_column("ventas", "registrada_offline")
    op.drop_column("ventas", "client_uuid")
