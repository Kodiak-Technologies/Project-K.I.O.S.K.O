"""Ingreso de mercadería: alta de producto nuevo y precio por total de línea.

Dos cambios que van juntos porque afectan la misma tabla:

1. `detalle_solicitud.producto_id` pasa a ser NULLABLE y se agregan los campos
   del producto propuesto (`nuevo_codigo`, `nuevo_nombre`, `nuevo_categoria_id`).
   El cajero puede transcribir una boleta con mercadería que todavía no está en
   el catálogo; el producto se crea recién al aprobar, que es cuando interviene
   alguien con `productos.crear`.

2. `precio_compra_unitario` pasa a `precio_compra_total`: la solicitud es una
   transcripción de boleta y la boleta dice "7 esponjas — S/ 20", no el unitario.
   OJO: no es un rename a secas. Las filas existentes guardan el UNITARIO, así
   que hay que multiplicar por `cantidad` para convertirlas al nuevo significado.

Revision ID: 0002_ingreso_producto_nuevo
Revises: 0001_esquema_inicial
Create Date: 2026-07-29
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0002_ingreso_producto_nuevo"
down_revision = "0001_esquema_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 1. Precio: unitario -> total de línea -------------------------------
    op.alter_column(
        "detalle_solicitud",
        "precio_compra_unitario",
        new_column_name="precio_compra_total",
    )
    # Conversión de los datos ya cargados: lo guardado era por unidad.
    op.execute(
        "UPDATE detalle_solicitud SET precio_compra_total = precio_compra_total * cantidad"
    )
    op.drop_constraint("chk_detsol_precio_no_negativo", "detalle_solicitud")
    op.create_check_constraint(
        "chk_detsol_precio_no_negativo", "detalle_solicitud", "precio_compra_total >= 0"
    )

    # --- 2. Producto propuesto ----------------------------------------------
    op.alter_column("detalle_solicitud", "producto_id", nullable=True)
    op.add_column("detalle_solicitud", sa.Column("nuevo_codigo", sa.String(60)))
    op.add_column("detalle_solicitud", sa.Column("nuevo_nombre", sa.String(150)))
    op.add_column(
        "detalle_solicitud",
        sa.Column(
            "nuevo_categoria_id",
            sa.Integer,
            sa.ForeignKey("categorias.id", ondelete="RESTRICT"),
        ),
    )
    op.add_column("detalle_solicitud", sa.Column("margen_ganancia", sa.Numeric(5, 2)))
    op.create_check_constraint(
        "chk_detsol_producto_o_nuevo",
        "detalle_solicitud",
        "producto_id IS NOT NULL"
        " OR (nuevo_codigo IS NOT NULL AND length(trim(nuevo_codigo)) > 0"
        "     AND nuevo_nombre IS NOT NULL AND length(trim(nuevo_nombre)) > 0)",
    )
    op.create_check_constraint(
        "chk_detsol_margen_no_negativo",
        "detalle_solicitud",
        "margen_ganancia IS NULL OR margen_ganancia >= 0",
    )
    # El índice pasa a parcial: las líneas con producto propuesto no indexan.
    op.drop_index("idx_detsol_producto", table_name="detalle_solicitud")
    op.create_index(
        "idx_detsol_producto",
        "detalle_solicitud",
        ["producto_id"],
        postgresql_where=sa.text("producto_id IS NOT NULL"),
    )

    # --- 3. Margen por defecto del negocio ----------------------------------
    op.add_column(
        "configuracion_negocio",
        sa.Column(
            "margen_ganancia_default",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="20",
        ),
    )


def downgrade() -> None:
    op.drop_column("configuracion_negocio", "margen_ganancia_default")

    op.drop_index("idx_detsol_producto", table_name="detalle_solicitud")
    op.create_index("idx_detsol_producto", "detalle_solicitud", ["producto_id"])
    op.drop_constraint("chk_detsol_margen_no_negativo", "detalle_solicitud")
    op.drop_constraint("chk_detsol_producto_o_nuevo", "detalle_solicitud")
    # Las líneas que proponían un producto no tienen `producto_id`: no hay forma
    # de representarlas en el esquema viejo, así que se van.
    op.execute("DELETE FROM detalle_solicitud WHERE producto_id IS NULL")
    op.drop_column("detalle_solicitud", "margen_ganancia")
    op.drop_column("detalle_solicitud", "nuevo_categoria_id")
    op.drop_column("detalle_solicitud", "nuevo_nombre")
    op.drop_column("detalle_solicitud", "nuevo_codigo")
    op.alter_column("detalle_solicitud", "producto_id", nullable=False)

    op.execute(
        "UPDATE detalle_solicitud SET precio_compra_total = precio_compra_total / cantidad"
    )
    op.drop_constraint("chk_detsol_precio_no_negativo", "detalle_solicitud")
    op.alter_column(
        "detalle_solicitud",
        "precio_compra_total",
        new_column_name="precio_compra_unitario",
    )
    op.create_check_constraint(
        "chk_detsol_precio_no_negativo",
        "detalle_solicitud",
        "precio_compra_unitario >= 0",
    )
