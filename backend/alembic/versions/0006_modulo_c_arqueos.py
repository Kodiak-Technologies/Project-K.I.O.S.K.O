"""Módulo C — HU-C07: arqueos de cierre de caja (esperado, contado, diferencia).

Revision ID: 0006_modulo_c_arqueos
Revises: 0005_modulo_c_pagos
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_modulo_c_arqueos"
down_revision = "0005_modulo_c_pagos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "arqueos",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("turno_id", sa.BigInteger, sa.ForeignKey("turnos_caja.id", ondelete="RESTRICT"),
                  nullable=False, unique=True),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cerrado_por", sa.String(100), nullable=False),
        sa.Column("efectivo_esperado", sa.Numeric(10, 2), nullable=False),
        sa.Column("efectivo_contado", sa.Numeric(10, 2), nullable=False),
        sa.Column("diferencia", sa.Numeric(10, 2), nullable=False),
        sa.Column("comentario", sa.Text),
        sa.Column("total_vendido", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("totales_por_metodo", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("arqueos")
