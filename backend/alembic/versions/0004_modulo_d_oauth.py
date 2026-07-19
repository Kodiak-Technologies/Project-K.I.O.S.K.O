"""Módulo D: tabla oauth_tokens para almacenar tokens OAuth de Google Drive.

Revision ID: 0004_modulo_d_oauth
Revises: 0003_modulo_d
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_modulo_d_oauth"
down_revision = "0003_modulo_d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("proveedor", sa.String(50), nullable=False),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=False),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usuario_id", sa.BigInteger, nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_oauth_tokens_proveedor", "oauth_tokens", ["proveedor"])


def downgrade() -> None:
    op.drop_table("oauth_tokens")
