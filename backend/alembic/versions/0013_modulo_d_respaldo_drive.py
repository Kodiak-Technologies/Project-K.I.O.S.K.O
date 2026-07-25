"""Módulo D: agregar usuario_id y drive_file_id a respaldos.

Revision ID: 0013_modulo_d_respaldo_drive
Revises: 73354c068ff5
Create Date: 2026-07-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_modulo_d_respaldo_drive"
down_revision = "73354c068ff5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "respaldos",
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "respaldos",
        sa.Column("drive_file_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_respaldos_usuario_id", "respaldos", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_respaldos_usuario_id", "respaldos")
    op.drop_column("respaldos", "drive_file_id")
    op.drop_column("respaldos", "usuario_id")
