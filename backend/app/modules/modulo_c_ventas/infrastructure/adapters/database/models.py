# Modelos SQLAlchemy (tablas) del módulo de ventas: ventas, detalles, cajas, aperturas, cierres.
# Nombres en español y snake_case. Todas las fechas TIMESTAMPTZ. Montos NUMERIC(10,2).
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base_model import Base


class TurnoCajaModel(Base):
    __tablename__ = "turnos_caja"
    __table_args__ = (
        CheckConstraint("monto_inicial >= 0", name="ck_turnos_monto_inicial_no_negativo"),
        # Solo puede existir UN turno abierto a la vez (una caja física en la tienda).
        Index(
            "ux_turnos_caja_abierto",
            "estado",
            unique=True,
            postgresql_where=text("estado = 'ABIERTO'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # RESTRICT: un usuario con turnos no puede desaparecer — preserva trazabilidad.
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    abierto_por: Mapped[str] = mapped_column(String(100), nullable=False)  # snapshot del nombre
    monto_inicial: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), default="ABIERTO", nullable=False)
    abierto_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    monto_final: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    usuario_cierre_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    cerrado_por: Mapped[str | None] = mapped_column(String(100))
    asignado_a_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT")
    )


class ArqueoCajaModel(Base):
    __tablename__ = "arqueos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Un arqueo por turno: el cierre no se repite ni se elimina (RF-17).
    turno_id: Mapped[int] = mapped_column(
        ForeignKey("turnos_caja.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
    )
    cerrado_por: Mapped[str] = mapped_column(String(100), nullable=False)
    efectivo_esperado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    efectivo_contado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    diferencia: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Obligatorio cuando hay descuadre: el ADMIN lo revisa desde su panel.
    comentario: Mapped[str | None] = mapped_column(Text)
    total_vendido: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    totales_por_metodo: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VentaModel(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        Index("ix_ventas_created_at", "created_at"),
        Index("ix_ventas_turno_id", "turno_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # RESTRICT en todo: una venta jamás pierde su turno ni su vendedor (trazabilidad).
    turno_id: Mapped[int] = mapped_column(
        ForeignKey("turnos_caja.id", ondelete="RESTRICT"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    vendedor: Mapped[str] = mapped_column(String(100), nullable=False)  # snapshot del nombre
    # Cliente asociado (obligatorio en ventas al fiado, RF-28).
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(20), nullable=False)  # resumen (MIXTO si >1)
    estado: Mapped[str] = mapped_column(String(20), default="COMPLETADA", nullable=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    # Modo offline (HU-C10, RF-26): UUID generado por el POS para que reintentar
    # la sincronización NUNCA duplique la venta (idempotencia).
    client_uuid: Mapped[str | None] = mapped_column(String(36), unique=True)
    registrada_offline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Momento REAL de la venta (en offline es anterior a created_at, que es la sincronización).
    vendida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    detalles: Mapped[list["DetalleVentaModel"]] = relationship(
        back_populates="venta", lazy="selectin", order_by="DetalleVentaModel.id"
    )
    pagos: Mapped[list["PagoVentaModel"]] = relationship(
        back_populates="venta", lazy="selectin", order_by="PagoVentaModel.id"
    )


class DetalleVentaModel(Base):
    __tablename__ = "detalles_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalles_cantidad_positiva"),
        Index("ix_detalles_venta_venta_id", "venta_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        ForeignKey("ventas.id", ondelete="RESTRICT"), nullable=False
    )
    # FK a la tabla de productos del Módulo B (clave foránea acordada entre módulos).
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False
    )
    # Snapshot del momento de la venta: cambiar el precio hoy no altera reportes históricos.
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_devuelta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    venta: Mapped[VentaModel] = relationship(back_populates="detalles")


class ClienteModel(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    alias: Mapped[str | None] = mapped_column(String(60))
    telefono: Mapped[str | None] = mapped_column(String(20))
    # 0 = sin límite definido; > 0 = tope de deuda (solo el ADMIN lo fija).
    limite_credito: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FiadoModel(Base):
    __tablename__ = "fiados"
    __table_args__ = (Index("ix_fiados_cliente_id", "cliente_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Un fiado nace de UNA venta (la venta fiada no suma efectivo a la caja).
    venta_id: Mapped[int] = mapped_column(
        ForeignKey("ventas.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False
    )
    monto_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    saldo_pendiente: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(12), default="PENDIENTE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AbonoModel(Base):
    __tablename__ = "abonos"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_abonos_monto_positivo"),
        Index("ix_abonos_fiado_id", "fiado_id"),
        Index("ix_abonos_turno_id", "turno_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fiado_id: Mapped[int] = mapped_column(
        ForeignKey("fiados.id", ondelete="RESTRICT"), nullable=False
    )
    # Turno en el que se cobró: si es efectivo, entra a ESE arqueo (RF-17).
    turno_id: Mapped[int] = mapped_column(
        ForeignKey("turnos_caja.id", ondelete="RESTRICT"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    registrado_por: Mapped[str] = mapped_column(String(100), nullable=False)
    metodo_pago_id: Mapped[int | None] = mapped_column(
        ForeignKey("metodos_pago.id", ondelete="RESTRICT")
    )
    codigo_metodo: Mapped[str] = mapped_column(String(20), nullable=False)
    es_efectivo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnulacionModel(Base):
    __tablename__ = "anulaciones"
    __table_args__ = (
        Index("ix_anulaciones_venta_id", "venta_id"),
        Index("ix_anulaciones_turno_id", "turno_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        ForeignKey("ventas.id", ondelete="RESTRICT"), nullable=False
    )
    # Turno en el que se HIZO el reverso: el efectivo sale de esa caja (RF-17).
    turno_id: Mapped[int] = mapped_column(
        ForeignKey("turnos_caja.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)  # ANULACION | DEVOLUCION
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    realizado_por: Mapped[str] = mapped_column(String(100), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    efectivo_devuelto: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    items: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MetodoPagoModel(Base):
    __tablename__ = "metodos_pago"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    # True = dinero físico que entra al cajón (cuenta para el arqueo, RF-17).
    es_efectivo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PagoVentaModel(Base):
    __tablename__ = "pagos_venta"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_pagos_monto_positivo"),
        Index("ix_pagos_venta_venta_id", "venta_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        ForeignKey("ventas.id", ondelete="RESTRICT"), nullable=False
    )
    metodo_pago_id: Mapped[int] = mapped_column(
        ForeignKey("metodos_pago.id", ondelete="RESTRICT"), nullable=False
    )
    # Snapshot: si el ADMIN renombra/desactiva un método, el historial no cambia.
    codigo_metodo: Mapped[str] = mapped_column(String(20), nullable=False)
    es_efectivo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    monto_recibido: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    venta: Mapped[VentaModel] = relationship(back_populates="pagos")
