# Modelos SQLAlchemy (tablas) del módulo de seguridad.
# Nombres en español y snake_case. Todas las fechas TIMESTAMPTZ.
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base_model import Base
from app.shared.kernel.soft_delete import SoftDeleteMixin


class RolModel(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)  # ADMIN | CAJERO
    descripcion: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class PermisoModel(Base):
    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)  # ej. ventas.anular
    descripcion: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class RolPermisoModel(Base):
    __tablename__ = "rol_permisos"

    rol_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    permiso_id: Mapped[int] = mapped_column(
        ForeignKey("permisos.id", ondelete="RESTRICT"), primary_key=True
    )


class UsuarioModel(Base, SoftDeleteMixin):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)  # nombre para mostrar
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    # RESTRICT: un rol con usuarios no puede borrarse — preserva la trazabilidad.
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    debe_cambiar_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SesionModel(Base):
    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # Solo el hash SHA-256 del refresh token; el token en claro nunca toca la BD.
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ip: Mapped[str] = mapped_column(String(45), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BitacoraAuditoriaModel(Base):
    __tablename__ = "bitacora_auditoria"
    __table_args__ = (
        Index("ix_bitacora_created_at", "created_at"),
        Index("ix_bitacora_usuario_id", "usuario_id"),
        Index("ix_bitacora_entidad", "entidad"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Nullable: un login fallido con username inexistente no tiene usuario asociado.
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    rol: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad_id: Mapped[str | None] = mapped_column(String(60))
    valor_anterior: Mapped[dict | None] = mapped_column(JSONB)
    valor_nuevo: Mapped[dict | None] = mapped_column(JSONB)
    motivo: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str] = mapped_column(String(45), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # INMUTABLE: sin UPDATE ni DELETE. Reforzado con trigger + REVOKE (ver migración 0001).


class ConfiguracionNegocioModel(Base):
    __tablename__ = "configuracion_negocio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # fila única, id = 1
    nombre_negocio: Mapped[str] = mapped_column(String(120), default="Mi Tienda", nullable=False)
    logo_url: Mapped[str] = mapped_column(Text, default="", nullable=False)  # URL o data-URI base64
    color_primario: Mapped[str] = mapped_column(String(20), default="#2563eb", nullable=False)
    color_secundario: Mapped[str] = mapped_column(String(20), default="#f59e0b", nullable=False)
    tipografia: Mapped[str] = mapped_column(String(60), default="Inter", nullable=False)
    session_ttl_admin_minutos: Mapped[int] = mapped_column(Integer, default=43200, nullable=False)
    session_ttl_cajero_minutos: Mapped[int] = mapped_column(Integer, default=720, nullable=False)
    max_intentos_login: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    minutos_bloqueo: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    # % de ganancia por defecto para el precio de venta de un producto dado de
    # alta desde un ingreso de mercadería. Pisable por línea al aprobar.
    margen_ganancia_default: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("20"), server_default="20", nullable=False
    )
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
