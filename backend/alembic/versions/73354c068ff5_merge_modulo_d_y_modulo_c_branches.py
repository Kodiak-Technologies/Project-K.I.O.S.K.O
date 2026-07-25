
"""merge modulo_d y modulo_c branches

Revision ID: 73354c068ff5
Revises: 0005_modulo_d_cliente_boleta, 0012_modulo_d_reestructuracion
Create Date: 2026-07-23 01:17:01.135312

"""
from alembic import op
import sqlalchemy as sa


revision = '73354c068ff5'
down_revision = ('0005_modulo_d_cliente_boleta', '0012_modulo_d_reestructuracion')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
