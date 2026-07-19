"""Módulo D: tablas de documentos (boletas, archivos_drive, notificaciones, config_notificaciones, respaldos).

Revision ID: 0003_modulo_d
Revises: 0001_modulo_a
Create Date: 2026-07-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_modulo_d"
down_revision = "0001_modulo_a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "boletas_clientes",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("venta_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("numero", sa.String(20), nullable=False, unique=True),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("emitida_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("url_pdf", sa.Text),
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

    op.create_table(
        "notificaciones",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column("mensaje", sa.Text, nullable=False),
        sa.Column("leida", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("entidad_origen", sa.String(60)),
        sa.Column("entidad_id", sa.String(60)),
        sa.Column("usuario_id", sa.BigInteger),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notificaciones_leida", "notificaciones", ["leida"])
    op.create_index("ix_notificaciones_created_at", "notificaciones", ["created_at"])
    op.create_index("ix_notificaciones_tipo", "notificaciones", ["tipo"])

    op.create_table(
        "config_notificaciones",
        sa.Column("id", sa.Integer, primary_key=True, server_default="1"),
        sa.Column("canal_telegram_activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("canal_correo_activo", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("nivel_detalle", sa.String(20), nullable=False, server_default="MEDIO"),
        sa.Column("telegram_chat_id", sa.String(100)),
        sa.Column("correo_destino", sa.String(120)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "respaldos",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("archivo_nombre", sa.String(255), nullable=False),
        sa.Column("tamano_bytes", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.Column("generado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_respaldos_estado", "respaldos", ["estado"])
    op.create_index("ix_respaldos_generado_en", "respaldos", ["generado_en"])


def downgrade() -> None:
    op.drop_table("respaldos")
    op.drop_table("config_notificaciones")
    op.drop_table("notificaciones")
    op.drop_table("archivos_drive")
    op.drop_table("boletas_clientes")
