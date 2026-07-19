"""Módulo C — HU-C04: catálogo de métodos de pago y pagos por venta (pago mixto).

Revision ID: 0005_modulo_c_pagos
Revises: 0004_modulo_c_ventas
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_modulo_c_pagos"
down_revision = "0004_modulo_c_ventas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metodos_pago",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("codigo", sa.String(20), nullable=False, unique=True),
        sa.Column("nombre", sa.String(50), nullable=False),
        sa.Column("es_efectivo", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    # Catálogo inicial; el ADMIN puede agregar/desactivar desde la interfaz (RF-20).
    op.execute(
        """
        INSERT INTO metodos_pago (codigo, nombre, es_efectivo, activo) VALUES
            ('EFECTIVO',      'Efectivo',      TRUE,  TRUE),
            ('YAPE',          'Yape',          FALSE, TRUE),
            ('PLIN',          'Plin',          FALSE, TRUE),
            ('TARJETA',       'Tarjeta',       FALSE, TRUE),
            ('TRANSFERENCIA', 'Transferencia', FALSE, TRUE)
        ON CONFLICT (codigo) DO NOTHING
        """
    )

    op.create_table(
        "pagos_venta",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("venta_id", sa.BigInteger, sa.ForeignKey("ventas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("metodo_pago_id", sa.Integer, sa.ForeignKey("metodos_pago.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("codigo_metodo", sa.String(20), nullable=False),
        sa.Column("es_efectivo", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("monto_recibido", sa.Numeric(10, 2)),
        sa.CheckConstraint("monto > 0", name="ck_pagos_monto_positivo"),
    )
    op.create_index("ix_pagos_venta_venta_id", "pagos_venta", ["venta_id"])


def downgrade() -> None:
    op.drop_table("pagos_venta")
    op.drop_table("metodos_pago")
