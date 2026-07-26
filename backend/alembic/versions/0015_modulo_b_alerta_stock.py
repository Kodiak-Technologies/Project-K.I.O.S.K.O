"""Módulo B: alerta única de stock mínimo por producto (HU-B13).

`productos.alerta_stock_notificada` se pone en TRUE cuando la alerta ya se
avisó y vuelve a FALSE sola cuando el producto se repone por encima de su
stock mínimo, para que no se repita el aviso en cada consulta.

Revision ID: 0015_modulo_b_alerta_stock
Revises: 0014_merge_heads
Create Date: 2026-07-25
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0015_modulo_b_alerta_stock"
down_revision = "0014_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "productos",
        sa.Column(
            "alerta_stock_notificada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("productos", "alerta_stock_notificada")
