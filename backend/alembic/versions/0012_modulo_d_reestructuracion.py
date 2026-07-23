"""Módulo D: reestructuración — eliminar boletas_clientes y archivos_drive,
simplificar config_notificaciones, agregar FK a notificaciones.

Revision ID: 0012_modulo_d_reestructuracion
Revises: 0011_modulo_c_asignar_turno
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op

revision = "0012_modulo_d_reestructuracion"
down_revision = "0011_modulo_c_asignar_turno"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Eliminar tablas de boletas (ya no se usan)
    op.drop_table("archivos_drive")
    op.drop_table("boletas_clientes")

    # 2. Simplificar config_notificaciones: eliminar campos de telegram/correo
    op.drop_column("config_notificaciones", "canal_telegram_activo")
    op.drop_column("config_notificaciones", "canal_correo_activo")
    op.drop_column("config_notificaciones", "telegram_chat_id")
    op.drop_column("config_notificaciones", "correo_destino")
    # Cambiar default de nivel_detalle de MEDIO a BAJO
    op.alter_column(
        "config_notificaciones",
        "nivel_detalle",
        server_default="BAJO",
    )

    # 3. Agregar FK a notificaciones: usuario_id → usuarios.id
    op.alter_column(
        "notificaciones",
        "usuario_id",
        existing_type=sa.BigInteger,
        nullable=True,
    )
    op.create_foreign_key(
        "fk_notificaciones_usuario_id",
        "notificaciones",
        "usuarios",
        ["usuario_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Agregar producto_id a notificaciones (para stock bajo)
    op.add_column(
        "notificaciones",
        sa.Column("producto_id", sa.BigInteger, nullable=True),
    )


def downgrade() -> None:
    # Revertir cambios en notificaciones
    op.drop_column("notificaciones", "producto_id")
    op.drop_constraint("fk_notificaciones_usuario_id", "notificaciones", type_="foreignkey")
    op.alter_column(
        "notificaciones",
        "usuario_id",
        existing_type=sa.BigInteger,
        nullable=True,
    )

    # Revertir config_notificaciones
    op.add_column("config_notificaciones", sa.Column("correo_destino", sa.String(120)))
    op.add_column("config_notificaciones", sa.Column("telegram_chat_id", sa.String(100)))
    op.add_column(
        "config_notificaciones",
        sa.Column("canal_correo_activo", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "config_notificaciones",
        sa.Column("canal_telegram_activo", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.alter_column(
        "config_notificaciones",
        "nivel_detalle",
        server_default="MEDIO",
    )

    # Recrear tablas de boletas
    op.create_table(
        "boletas_clientes",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("venta_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("numero", sa.String(20), nullable=False, unique=True),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("emitida_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("url_pdf", sa.Text),
        sa.Column("cliente_nombre", sa.String(120)),
    )
    op.create_index("ix_boletas_venta_id", "boletas_clientes", ["venta_id"])
    op.create_index("ix_boletas_numero", "boletas_clientes", ["numero"])
    op.create_index("ix_boletas_emitida_en", "boletas_clientes", ["emitida_en"])

    op.create_table(
        "archivos_drive",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("boleta_id", sa.BigInteger, sa.ForeignKey("boletas_clientes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("archivo_nombre", sa.String(255), nullable=False),
        sa.Column("carpeta", sa.String(255), nullable=False, server_default=""),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.Column("intentos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("drive_file_id", sa.String(255)),
        sa.Column("error_mensaje", sa.Text),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_archivos_drive_boleta_id", "archivos_drive", ["boleta_id"])
    op.create_index("ix_archivos_drive_estado", "archivos_drive", ["estado"])
