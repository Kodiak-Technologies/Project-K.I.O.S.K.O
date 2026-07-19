"""Módulo C — Cierre automático: arqueos.usuario_id pasa a nullable.

Revision ID: 0010_modulo_c_cierre_automatico
Revises: 0009_modulo_c_offline
Create Date: 2026-07-17

Permite que el campo usuario_id en la tabla arqueos sea NULL cuando el cierre
lo realiza el sistema automáticamente (turno olvidado al final del día),
en lugar de un usuario humano.
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_modulo_c_cierre_automatico"
down_revision = "0009_modulo_c_offline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Hacer nullable usuario_id para soportar cierres automáticos por Sistema.
    op.alter_column(
        "arqueos",
        "usuario_id",
        existing_type=sa.BigInteger(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    # Revertir a NOT NULL (asume que no hay filas con NULL en producción).
    op.alter_column(
        "arqueos",
        "usuario_id",
        existing_type=sa.BigInteger(),
        nullable=False,
        existing_nullable=True,
    )
