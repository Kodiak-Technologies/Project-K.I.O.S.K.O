import sqlalchemy as sa
from alembic import op

revision = "0011_modulo_c_asignar_turno"
down_revision = "0010_modulo_c_cierre_automatico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("turnos_caja", sa.Column("asignado_a_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_turnos_caja_asignado_a_id",
        "turnos_caja",
        "usuarios",
        ["asignado_a_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_turnos_caja_asignado_a_id", "turnos_caja", type_="foreignkey")
    op.drop_column("turnos_caja", "asignado_a_id")
