"""Módulo C — HU-C09: clientes, fiados (cuentas por cobrar) y abonos.

Revision ID: 0008_modulo_c_fiados
Revises: 0007_modulo_c_anulaciones
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_modulo_c_fiados"
down_revision = "0007_modulo_c_anulaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("alias", sa.String(60)),
        sa.Column("telefono", sa.String(20)),
        sa.Column("limite_credito", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clientes_nombre", "clientes", ["nombre"])

    op.create_table(
        "fiados",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("venta_id", sa.BigInteger, sa.ForeignKey("ventas.id", ondelete="RESTRICT"),
                  nullable=False, unique=True),
        sa.Column("cliente_id", sa.BigInteger, sa.ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("monto_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("saldo_pendiente", sa.Numeric(10, 2), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="PENDIENTE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fiados_cliente_id", "fiados", ["cliente_id"])

    op.create_table(
        "abonos",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("fiado_id", sa.BigInteger, sa.ForeignKey("fiados.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("turno_id", sa.BigInteger, sa.ForeignKey("turnos_caja.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("registrado_por", sa.String(100), nullable=False),
        sa.Column("metodo_pago_id", sa.Integer, sa.ForeignKey("metodos_pago.id", ondelete="RESTRICT")),
        sa.Column("codigo_metodo", sa.String(20), nullable=False),
        sa.Column("es_efectivo", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("monto > 0", name="ck_abonos_monto_positivo"),
    )
    op.create_index("ix_abonos_fiado_id", "abonos", ["fiado_id"])
    op.create_index("ix_abonos_turno_id", "abonos", ["turno_id"])

    # La venta fiada queda asociada a su cliente.
    op.add_column(
        "ventas",
        sa.Column("cliente_id", sa.BigInteger, sa.ForeignKey("clientes.id", ondelete="RESTRICT")),
    )

    # El FIADO es un método de pago diferenciado (RF-28): no es efectivo y no
    # puede desactivarse (protegido en el caso de uso).
    op.execute(
        """
        INSERT INTO metodos_pago (codigo, nombre, es_efectivo, activo)
        VALUES ('FIADO', 'Fiado (a crédito)', FALSE, TRUE)
        ON CONFLICT (codigo) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_column("ventas", "cliente_id")
    op.drop_table("abonos")
    op.drop_table("fiados")
    op.drop_table("clientes")
