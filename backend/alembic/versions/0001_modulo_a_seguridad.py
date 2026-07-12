"""Módulo A: tablas de seguridad, accesos, configuración y bitácora inmutable.

Revision ID: 0001_modulo_a
Revises:
Create Date: 2026-07-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001_modulo_a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(30), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=False, server_default=""),
    )

    op.create_table(
        "permisos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("codigo", sa.String(60), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=False, server_default=""),
    )

    op.create_table(
        "rol_permisos",
        sa.Column("rol_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("permiso_id", sa.Integer, sa.ForeignKey("permisos.id", ondelete="RESTRICT"), primary_key=True),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("username", sa.String(30), nullable=False, unique=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("rol_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("debe_cambiar_password", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("intentos_fallidos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True)),
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Borrado lógico transversal: nada se elimina físicamente.
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", sa.BigInteger),
    )
    op.create_index("ix_usuarios_username", "usuarios", ["username"])

    op.create_table(
        "sesiones",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(400), nullable=False, server_default=""),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sesiones_usuario_id", "sesiones", ["usuario_id"])

    op.create_table(
        "bitacora_auditoria",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT")),
        sa.Column("rol", sa.String(30), nullable=False, server_default=""),
        sa.Column("accion", sa.String(60), nullable=False),
        sa.Column("entidad", sa.String(60), nullable=False),
        sa.Column("entidad_id", sa.String(60)),
        sa.Column("valor_anterior", JSONB),
        sa.Column("valor_nuevo", JSONB),
        sa.Column("motivo", sa.Text),
        sa.Column("ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(400), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bitacora_created_at", "bitacora_auditoria", ["created_at"])
    op.create_index("ix_bitacora_usuario_id", "bitacora_auditoria", ["usuario_id"])
    op.create_index("ix_bitacora_entidad", "bitacora_auditoria", ["entidad"])

    # La bitácora es INMUTABLE incluso a nivel de base de datos: cualquier UPDATE
    # o DELETE (venga de quien venga, incluso superusuario de la app) lanza excepción.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'La bitácora de auditoría es inmutable: no se permite % sobre ella', TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_bitacora_inmutable
        BEFORE UPDATE OR DELETE ON bitacora_auditoria
        FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable()
        """
    )

    op.create_table(
        "configuracion_negocio",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre_negocio", sa.String(120), nullable=False, server_default="Mi Tienda"),
        sa.Column("logo_url", sa.Text, nullable=False, server_default=""),
        sa.Column("color_primario", sa.String(20), nullable=False, server_default="#2563eb"),
        sa.Column("color_secundario", sa.String(20), nullable=False, server_default="#f59e0b"),
        sa.Column("tipografia", sa.String(60), nullable=False, server_default="Inter"),
        sa.Column("session_ttl_admin_minutos", sa.Integer, nullable=False, server_default="43200"),
        sa.Column("session_ttl_cajero_minutos", sa.Integer, nullable=False, server_default="720"),
        sa.Column("max_intentos_login", sa.Integer, nullable=False, server_default="3"),
        sa.Column("minutos_bloqueo", sa.Integer, nullable=False, server_default="15"),
        sa.Column("updated_by", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="RESTRICT")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("configuracion_negocio")
    op.execute("DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON bitacora_auditoria")
    op.execute("DROP FUNCTION IF EXISTS bitacora_inmutable")
    op.drop_table("bitacora_auditoria")
    op.drop_table("sesiones")
    op.drop_table("usuarios")
    op.drop_table("rol_permisos")
    op.drop_table("permisos")
    op.drop_table("roles")
