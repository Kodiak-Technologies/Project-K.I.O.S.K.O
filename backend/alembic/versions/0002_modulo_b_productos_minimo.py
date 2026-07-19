"""Módulo B (mínimo): productos y categorías para habilitar el POS del Módulo C.

Implementación temporal de Clever siguiendo el contrato de docs/FRONTEND_CONTRATOS_API.md;
Brayan la amplía con el resto de tablas de su módulo (ingresos, movimientos, mermas, etc.).

Revision ID: 0002_modulo_b_min
Revises: 0001_modulo_a
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_modulo_b_min"
down_revision = "0001_modulo_a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(80), nullable=False, unique=True),
    )

    op.create_table(
        "productos",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("codigo", sa.String(60), nullable=False, unique=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("categoria_id", sa.Integer, sa.ForeignKey("categorias.id", ondelete="RESTRICT")),
        sa.Column("precio", sa.Numeric(10, 2), nullable=False),
        sa.Column("stock", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stock_minimo", sa.Integer, nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Borrado lógico transversal (nada se elimina físicamente).
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", sa.BigInteger),
        # El stock nunca queda negativo (RF-08), también a nivel de BD.
        sa.CheckConstraint("stock >= 0", name="ck_productos_stock_no_negativo"),
    )
    op.create_index("ix_productos_codigo", "productos", ["codigo"])
    op.create_index("ix_productos_nombre", "productos", ["nombre"])


def downgrade() -> None:
    op.drop_table("productos")
    op.drop_table("categorias")
