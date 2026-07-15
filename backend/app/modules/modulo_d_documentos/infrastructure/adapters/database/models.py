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


class BoletaModel(Base):
    __tablename__ = "boletas_clientes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    emitida_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    url_pdf: Mapped[str | None] = mapped_column(Text)


class ArchivoDriveModel(Base):
    __tablename__ = "archivos_drive"
    __table_args__ = (
        Index("ix_archivos_drive_boleta_id", "boleta_id"),
        Index("ix_archivos_drive_estado", "estado"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    boleta_id: Mapped[int] = mapped_column(
        ForeignKey("boletas_clientes.id", ondelete="RESTRICT"), nullable=False
    )
    archivo_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    carpeta: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", nullable=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    drive_file_id: Mapped[str | None] = mapped_column(String(255))
    error_mensaje: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


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
    usuario_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConfigNotificacionesModel(Base):
    __tablename__ = "config_notificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    canal_telegram_activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    canal_correo_activo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nivel_detalle: Mapped[str] = mapped_column(String(20), default="MEDIO", nullable=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100))
    correo_destino: Mapped[str | None] = mapped_column(String(120))
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
