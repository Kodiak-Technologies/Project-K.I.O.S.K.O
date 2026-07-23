from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base_model import Base


class NotificacionModel(Base):
    __tablename__ = "notificaciones"
    __table_args__ = (
        Index("ix_notificaciones_leida", "leida"),
        Index("ix_notificaciones_created_at", "created_at"),
        Index("ix_notificaciones_tipo", "tipo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    entidad_origen: Mapped[str | None] = mapped_column(String(60))
    entidad_id: Mapped[str | None] = mapped_column(String(60))
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    producto_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConfigNotificacionesModel(Base):
    __tablename__ = "config_notificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    nivel_detalle: Mapped[str] = mapped_column(String(20), default="BAJO", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RespaldoModel(Base):
    __tablename__ = "respaldos"
    __table_args__ = (
        Index("ix_respaldos_estado", "estado"),
        Index("ix_respaldos_generado_en", "generado_en"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    archivo_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", nullable=False)
    generado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OAuthTokenModel(Base):
    __tablename__ = "oauth_tokens"
    __table_args__ = (
        Index("ix_oauth_tokens_proveedor", "proveedor"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    proveedor: Mapped[str] = mapped_column(String(50), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
