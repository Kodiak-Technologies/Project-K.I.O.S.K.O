# Entidades de dominio: Venta, DetalleVenta, Caja, AperturaCaja, CierreCaja, MedioPago.
# Python puro: sin FastAPI ni SQLAlchemy.
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.modules.modulo_c_ventas.domain.value_objects import (
    TURNO_ABIERTO,
    VENTA_ANULADA,
    VENTA_COMPLETADA,
)


@dataclass
class TurnoCaja:
    """Un turno de caja: apertura manual con el efectivo contado, cierre con arqueo.

    La apertura y el cierre son visibles para TODOS los usuarios (cajeros y admin):
    en un cambio de turno, el que entra ve con cuánto abrió y cerró el anterior.
    """

    id: int | None
    usuario_id: int
    abierto_por: str  # nombre para mostrar (snapshot: no cambia si renombran al usuario)
    monto_inicial: Decimal
    estado: str = TURNO_ABIERTO
    abierto_en: datetime | None = None
    cerrado_en: datetime | None = None
    monto_final: Decimal | None = None  # efectivo REAL contado al cierre
    usuario_cierre_id: int | None = None
    cerrado_por: str | None = None

    def esta_abierto(self) -> bool:
        return self.estado == TURNO_ABIERTO


@dataclass
class ProductoVendible:
    """Lo mínimo que Ventas necesita saber de un producto del inventario (Módulo B).

    Llega a través de ProductoStockPort: este módulo nunca importa código interno
    del módulo de inventario (docs/ARQUITECTURA.md §4).
    """

    id: int
    codigo: str
    nombre: str
    precio: Decimal
    stock: int
    activo: bool


@dataclass
class DetalleVenta:
    """Una línea del carrito. Nombre y precio son SNAPSHOT del momento de la venta:
    si mañana cambia el precio, los reportes históricos no se alteran (RF-18)."""

    id: int | None
    producto_id: int
    nombre: str
    precio_unitario: Decimal
    cantidad: int
    cantidad_devuelta: int = 0

    @property
    def subtotal(self) -> Decimal:
        return self.precio_unitario * self.cantidad


@dataclass
class Venta:
    id: int | None
    turno_id: int
    usuario_id: int
    vendedor: str  # snapshot del nombre
    total: Decimal
    metodo_pago: str  # resumen: EFECTIVO | YAPE | ... | MIXTO | FIADO
    estado: str = VENTA_COMPLETADA
    detalles: list[DetalleVenta] = field(default_factory=list)
    motivo_anulacion: str | None = None
    created_at: datetime | None = None

    @property
    def anulada(self) -> bool:
        return self.estado == VENTA_ANULADA
