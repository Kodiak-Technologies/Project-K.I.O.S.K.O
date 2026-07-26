"""Esquema inicial completo del sistema.

Colapsa las 20 migraciones anteriores en una sola. Aquellas se habían vuelto
inconsultables: tenían dos *heads*, una revisión huérfana (`0013_modulo_d_
respaldo_drive`, aplicada en la BD compartida pero inexistente en esta rama) y
migraciones que hacían ALTER sobre tablas que ninguna creaba.

La fuente de verdad del esquema es `db/schema.sql`, que se genera a partir de
los modelos SQLAlchemy. Esta migración simplemente lo ejecuta, así que no puede
desincronizarse del código.

Revision ID: 0001_esquema_inicial
Revises:
Create Date: 2026-07-26
"""
from pathlib import Path

from alembic import op


# revision identifiers, used by Alembic.
revision = "0001_esquema_inicial"
down_revision = None
branch_labels = None
depends_on = None

_SCHEMA = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def upgrade() -> None:
    sql = _SCHEMA.read_text(encoding="utf-8")
    # El bloque de RESET viene comentado en el archivo: acá no se toca nada
    # que no sea crear el esquema.
    op.execute(sql)


def downgrade() -> None:
    # Volver atrás del esquema inicial es borrar todo: se hace explícito en vez
    # de dejar un downgrade a medias.
    op.execute("DROP SCHEMA public CASCADE")
    op.execute("CREATE SCHEMA public")
