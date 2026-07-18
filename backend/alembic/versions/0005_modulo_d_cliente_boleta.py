"""Módulo D: agregar campo cliente_nombre a boletas_clientes.

Revision ID: 0005_modulo_d_cliente_boleta
Revises: 0004_modulo_d_oauth
Create Date: 2026-07-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_modulo_d_cliente_boleta"
down_revision = "0004_modulo_d_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "boletas_clientes",
        sa.Column("cliente_nombre", sa.String(120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("boletas_clientes", "cliente_nombre")
