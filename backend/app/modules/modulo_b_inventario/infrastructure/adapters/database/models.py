# Modelos SQLAlchemy (tablas) del módulo de inventario: productos, categorías, almacenes, ingresos, movimientos.
#
# EXTENDIDO en PR1: 7 modelos nuevos + snapshots en `ProductoModel` y
# `CategoriaModel`. Solo se AGREGAN columnas (compromiso con Módulo C: D-08).
# Convenciones:
#   - `BigInteger` para ids de entidades operativas (coincide con `usuarios.id`).
#   - `Numeric(10, 2)` para precios, `Numeric(12, 2)` para deudas.
#   - `DateTime(timezone=True)` con `server_default=func.now()` para timestamps.
#   - `CheckConstraint` cuando aplica (cantidades, enums, no-negativos).
#   - `SoftDeleteMixin` para entidades con borrado lógico.
#   - `Index` en FKs y columnas frecuentemente filtradas.
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
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
from app.shared.kernel.soft_delete import SoftDeleteMixin


class CategoriaModel(Base, SoftDeleteMixin):
    """EXTENDIDA en PR1: `descripcion`, `creado_por`, `creado_por_nombre`,
    `created_at`, `updated_at` (los 2 últimos con default now()).
    La tabla mínima previa (de Clever) ya tenía `id` y `nombre`.
    """

    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    creado_por: Mapped[int | None] = mapped_column(BigInteger)
    creado_por_nombre: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProductoModel(Base, SoftDeleteMixin):
    """EXTENDIDA en PR1: `precio_compra_actual`, `es_codigo_interno`, `foto_url`,
    snapshots `creado_por`/`creado_por_nombre`, `actualizado_por`/`actualizado_por_nombre`.
    Las columnas nuevas tienen defaults (NOT NULL DEFAULT 0/FALSE o NULL) para no
    romper filas existentes al aplicar la migración aditiva.
    """

    __tablename__ = "productos"
    __table_args__ = (
        # El stock NUNCA queda negativo (RF-08): reforzado también a nivel de BD.
        CheckConstraint("stock >= 0", name="ck_productos_stock_no_negativo"),
        # precio_compra_actual >= 0 (PR1)
        CheckConstraint(
            "precio_compra_actual >= 0", name="ck_productos_precio_compra_no_negativo"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Código de barras escaneado o código interno (PAP-001). Único en todo el catálogo.
    codigo: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id", ondelete="RESTRICT")
    )
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # PR1: precio de compra actual (para márgenes; default 0 para compat con filas preexistentes)
    precio_compra_actual: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    # PR1: TRUE si el producto no tiene código de barras y se le asignó código interno
    es_codigo_interno: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Nota: la columna `foto_url` sigue existiendo en la BD pero YA NO se mapea:
    # los productos no llevan foto (decisión 2026-07-25).
    # HU-B13: alerta única de stock mínimo. Se pone en TRUE cuando se avisa y
    # vuelve a FALSE sola al reponer por encima del mínimo.
    alerta_stock_notificada: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa.false(), nullable=False
    )
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_minimo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # PR1: snapshots de auditoría (D-03)
    creado_por: Mapped[int | None] = mapped_column(BigInteger)
    creado_por_nombre: Mapped[str | None] = mapped_column(String(100))
    actualizado_por: Mapped[int | None] = mapped_column(BigInteger)
    actualizado_por_nombre: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProveedorModel(Base, SoftDeleteMixin):
    """Maestro de proveedores con control de deuda (HU-B14, D-12)."""

    __tablename__ = "proveedores"
    __table_args__ = (
        CheckConstraint("deuda_actual >= 0", name="ck_proveedores_deuda_no_negativa"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(120), nullable=False)
    ruc: Mapped[str | None] = mapped_column(String(20), index=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deuda_actual: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    creado_por: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creado_por_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SolicitudIngresoModel(Base, SoftDeleteMixin):
    """Solicitudes de ingreso con flujo de aprobación en 2 pasos (D-09)."""

    __tablename__ = "solicitudes_ingreso"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('Pendiente','Aprobada','Rechazada')",
            name="chk_solicitudes_estado",
        ),
        CheckConstraint(
            "(estado = 'Rechazada' AND motivo_rechazo IS NOT NULL "
            "AND length(trim(motivo_rechazo)) > 0) OR estado <> 'Rechazada'",
            name="chk_solicitudes_rechazo_tiene_motivo",
        ),
        CheckConstraint(
            "(estado = 'Pendiente' AND revisado_por IS NULL AND revisado_en IS NULL) OR "
            "(estado IN ('Aprobada','Rechazada') AND revisado_por IS NOT NULL "
            "AND revisado_en IS NOT NULL)",
            name="chk_solicitudes_revisado_consistente",
        ),
        Index("idx_solicitudes_estado", "estado", "created_at"),
        Index("idx_solicitudes_solicitante", "solicitado_por", "created_at"),
        Index("idx_solicitudes_proveedor", "proveedor_id"),
        # sdd/modulo-b-aprobaciones-detalle-editar
        Index(
            "idx_solicitudes_editado_en",
            "editado_en",
            postgresql_where=sa.text("editado_en IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    proveedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("proveedores.id", ondelete="RESTRICT")
    )
    estado: Mapped[str] = mapped_column(String(20), default="Pendiente", nullable=False)
    foto_boleta_url: Mapped[str] = mapped_column(Text, nullable=False)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)
    solicitado_por: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    solicitado_por_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    revisado_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    revisado_por_nombre: Mapped[str | None] = mapped_column(String(100))
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # sdd/modulo-b-aprobaciones-detalle-editar: free-text edit justification (PATCH allowlist).
    motivo: Mapped[str | None] = mapped_column(Text)
    # Edit audit triple (denormalized; SET NULL on user delete to preserve history).
    editado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    editado_por_nombre: Mapped[str | None] = mapped_column(String(100))
    editado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DetalleSolicitudModel(Base):
    """Líneas de una solicitud de ingreso. Sin soft delete (CASCADE en BD)."""

    __tablename__ = "detalle_solicitud"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_detsol_cantidad_positiva"),
        CheckConstraint(
            "precio_compra_unitario >= 0", name="chk_detsol_precio_no_negativo"
        ),
        Index("idx_detsol_solicitud", "solicitud_id"),
        Index("idx_detsol_producto", "producto_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(
        ForeignKey("solicitudes_ingreso.id", ondelete="CASCADE"), nullable=False
    )
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_compra_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PagoProveedorModel(Base, SoftDeleteMixin):
    """Historial de pagos/compras a crédito (D-12, D-15). Append-only por convención."""

    __tablename__ = "pagos_proveedor"
    __table_args__ = (
        CheckConstraint("monto > 0", name="chk_pagos_monto_positivo"),
        CheckConstraint(
            "tipo IN ('compra_credito','pago')", name="chk_pagos_tipo"
        ),
        CheckConstraint(
            "tipo = 'compra_credito' OR solicitud_ingreso_id IS NULL",
            name="chk_pagos_solicitud_solo_en_compra",
        ),
        Index("idx_pagos_proveedor", "proveedor_id", "fecha"),
        Index("idx_pagos_tipo", "tipo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(
        ForeignKey("proveedores.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    concepto: Mapped[str | None] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(Date, nullable=False)
    solicitud_ingreso_id: Mapped[int | None] = mapped_column(
        ForeignKey("solicitudes_ingreso.id", ondelete="RESTRICT")
    )
    registrado_por: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    registrado_por_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MovimientoInventarioModel(Base):
    """Bitácora append-only de variaciones de stock (D-07). Sin soft delete."""

    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        CheckConstraint("cantidad <> 0", name="chk_mov_cantidad_no_cero"),
        CheckConstraint(
            "tipo IN ('ingreso','ajuste','venta','devolucion')",
            name="chk_mov_tipo",
        ),
        CheckConstraint(
            "(tipo IN ('ingreso','devolucion') AND cantidad > 0) OR "
            "(tipo = 'venta' AND cantidad < 0) OR "
            "(tipo = 'ajuste')",
            name="chk_mov_signo_por_tipo",
        ),
        CheckConstraint(
            "tipo <> 'ingreso' OR solicitud_ingreso_id IS NOT NULL",
            name="chk_mov_ingreso_tiene_solicitud",
        ),
        # El ajuste manual (reemplazo del flujo de mermas) siempre lleva
        # motivo: es la única trazabilidad del faltante.
        CheckConstraint(
            "tipo <> 'ajuste' OR (motivo IS NOT NULL AND length(trim(motivo)) > 0)",
            name="chk_mov_ajuste_tiene_motivo",
        ),
        Index("idx_mov_producto_fecha", "producto_id", "created_at"),
        Index("idx_mov_tipo", "tipo"),
        Index("idx_mov_solicitud", "solicitud_ingreso_id"),
        Index("idx_mov_created_at_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(200))
    solicitud_ingreso_id: Mapped[int | None] = mapped_column(
        ForeignKey("solicitudes_ingreso.id", ondelete="RESTRICT")
    )
    registrado_por: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    registrado_por_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HistorialPrecioModel(Base):
    """Bitácora append-only de cambios de precio (D-06, HU-B11). El trigger
    `trg_historial_precios_no_update` en BD rechaza UPDATE/DELETE."""

    __tablename__ = "historial_precios"
    __table_args__ = (
        CheckConstraint("precio_nuevo >= 0", name="chk_historial_precio_no_negativo"),
        CheckConstraint(
            "tipo_precio IN ('venta','compra')", name="chk_historial_tipo"
        ),
        Index("idx_historial_producto_fecha", "producto_id", "tipo_precio", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False
    )
    precio_anterior: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # NULL en alta
    precio_nuevo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tipo_precio: Mapped[str] = mapped_column(String(20), nullable=False)
    modificado_por: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    modificado_por_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
