"""Modulo B: edit audit fields + free-text motivo on solicitudes_ingreso + mermas.

Prerequisite for PATCH /ingresos/{id} and PATCH /mermas/{id} (sdd/modulo-b-aprobaciones-detalle-editar).

Revision ID: 0013_modulo_b_editar_ingreso_merma
Revises: 0012_modulo_d_reestructuracion
Create Date: 2026-07-25
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0013_modulo_b_editar_ingreso_merma"
down_revision = "0012_modulo_d_reestructuracion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # solicitudes_ingreso
    op.add_column(
        "solicitudes_ingreso",
        sa.Column("motivo", sa.Text(), nullable=True),
    )
    op.add_column(
        "solicitudes_ingreso",
        sa.Column("editado_por", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "solicitudes_ingreso",
        sa.Column("editado_por_nombre", sa.String(100), nullable=True),
    )
    op.add_column(
        "solicitudes_ingreso",
        sa.Column("editado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_solicitudes_editado_por",
        "solicitudes_ingreso",
        "usuarios",
        ["editado_por"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_solicitudes_editado_en",
        "solicitudes_ingreso",
        ["editado_en"],
        unique=False,
        postgresql_where=sa.text("editado_en IS NOT NULL AND deleted_at IS NULL"),
    )

    # mermas — NO motivo (the existing motivo column is the enum
    # vencimiento|rotura|otro; the spec's PATCH allowlist on mermas
    # does NOT add a new motivo field).
    op.add_column(
        "mermas",
        sa.Column("editado_por", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "mermas",
        sa.Column("editado_por_nombre", sa.String(100), nullable=True),
    )
    op.add_column(
        "mermas",
        sa.Column("editado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_mermas_editado_por",
        "mermas",
        "usuarios",
        ["editado_por"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_mermas_editado_en",
        "mermas",
        ["editado_en"],
        unique=False,
        postgresql_where=sa.text("editado_en IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    # Reverse order
    op.drop_index("idx_mermas_editado_en", table_name="mermas")
    op.drop_constraint("fk_mermas_editado_por", "mermas", type_="foreignkey")
    op.drop_column("mermas", "editado_en")
    op.drop_column("mermas", "editado_por_nombre")
    op.drop_column("mermas", "editado_por")

    op.drop_index("idx_solicitudes_editado_en", table_name="solicitudes_ingreso")
    op.drop_constraint(
        "fk_solicitudes_editado_por", "solicitudes_ingreso", type_="foreignkey"
    )
    op.drop_column("solicitudes_ingreso", "editado_en")
    op.drop_column("solicitudes_ingreso", "editado_por_nombre")
    op.drop_column("solicitudes_ingreso", "editado_por")
    op.drop_column("solicitudes_ingreso", "motivo")
