"""Quitar el margen de ganancia del ingreso de mercadería.

Aprobar un ingreso calculaba el precio de venta del producto que se daba de
alta: costo unitario + un margen (el de la línea, o el 20% por defecto del
negocio). Eso hacía que una compra terminara fijando el precio del catálogo y,
por lo tanto, el del punto de venta, sin que nadie lo decidiera.

Ahora el ingreso no fija precios de venta: el producto nuevo nace en S/ 0 y el
precio se pone a mano desde el catálogo. Las dos columnas que sostenían el
cálculo quedan sin uso y se eliminan:

  - `detalle_solicitud.margen_ganancia` (+ su CHECK)
  - `configuracion_negocio.margen_ganancia_default`

El downgrade las repone con el default histórico (20%), pero no puede recuperar
los valores por línea que hubiera cargados.

Revision ID: 0003_quitar_margen_ganancia
Revises: 0002_ingreso_producto_nuevo
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0003_quitar_margen_ganancia"
down_revision = "0002_ingreso_producto_nuevo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("chk_detsol_margen_no_negativo", "detalle_solicitud")
    op.drop_column("detalle_solicitud", "margen_ganancia")
    op.drop_column("configuracion_negocio", "margen_ganancia_default")


def downgrade() -> None:
    op.add_column(
        "configuracion_negocio",
        sa.Column(
            "margen_ganancia_default",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="20",
        ),
    )
    op.add_column("detalle_solicitud", sa.Column("margen_ganancia", sa.Numeric(5, 2)))
    op.create_check_constraint(
        "chk_detsol_margen_no_negativo",
        "detalle_solicitud",
        "margen_ganancia IS NULL OR margen_ganancia >= 0",
    )
