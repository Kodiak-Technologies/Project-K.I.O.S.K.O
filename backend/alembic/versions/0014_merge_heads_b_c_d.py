"""Merge de las dos cabezas abiertas: Módulo B (0013) y el merge C/D (73354c068ff5).

Con dos heads simultáneas, `alembic upgrade head` abortaba con
"Multiple head revisions are present"; había que saber de memoria el id exacto
para poder migrar. Esta revisión vacía las une.

Revision ID: 0014_merge_heads
Revises: 0013_modulo_b_editar_ingreso_merma, 73354c068ff5
Create Date: 2026-07-25
"""

# revision identifiers, used by Alembic.
revision = "0014_merge_heads"
down_revision = ("0013_modulo_b_editar_ingreso_merma", "73354c068ff5")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge sin cambios de esquema."""


def downgrade() -> None:
    """Merge sin cambios de esquema."""
