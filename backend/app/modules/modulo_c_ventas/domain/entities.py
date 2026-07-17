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
class ArqueoCaja:
    """El arqueo del cierre (RF-17): el sistema SUGIERE el efectivo esperado
    (inicial + ventas en efectivo ± movimientos) y el cajero registra lo contado.
    Si hay diferencia, el comentario es obligatorio y el ADMIN lo ve en su panel.
    """

    id: int | None
    turno_id: int
    usuario_id: int
    cerrado_por: str
    efectivo_esperado: Decimal
    efectivo_contado: Decimal
    diferencia: Decimal  # contado - esperado (negativo = faltante)
    comentario: str | None = None
    total_vendido: Decimal = Decimal("0")
    # Desglose informativo de lo vendido por método: el dinero digital (Yape,
    # tarjeta...) existe pero NO está físicamente en el cajón.
    totales_por_metodo: dict[str, float] | None = None
    created_at: datetime | None = None

    @property
    def cuadrado(self) -> bool:
        return self.diferencia == Decimal("0")


@dataclass
class ResumenCaja:
    """Foto del turno abierto para la pantalla de cierre (no se persiste)."""

    turno: "TurnoCaja"
    efectivo_esperado: Decimal
    monto_inicial: Decimal
    ventas_efectivo: Decimal
    abonos_efectivo: Decimal  # fiados cobrados en efectivo (HU-C09)
    devoluciones_efectivo: Decimal  # dinero devuelto de la caja (HU-C08)
    totales_por_metodo: dict[str, float]
    total_vendido: Decimal
    numero_ventas: int


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
class MetodoPago:
    """Método de pago del catálogo (el ADMIN puede agregar o desactivar, RF-20).

    es_efectivo distingue el dinero FÍSICO que entra a la caja del dinero digital
    (Yape, tarjeta...) que existe pero no está en el cajón: el arqueo solo cuadra
    contra el efectivo (RF-17).
    """

    id: int | None
    codigo: str  # EFECTIVO | YAPE | PLIN | TARJETA | TRANSFERENCIA | FIADO | ...
    nombre: str
    es_efectivo: bool = False
    activo: bool = True


@dataclass
class PagoVenta:
    """Una parte del pago de la venta. Una venta simple tiene un solo pago;
    una mixta (mitad efectivo, mitad Yape) tiene varios (RF-20)."""

    id: int | None
    codigo_metodo: str
    monto: Decimal
    es_efectivo: bool = False
    # Con cuánto pagó el cliente (solo efectivo): permite calcular el vuelto.
    monto_recibido: Decimal | None = None
    metodo_pago_id: int | None = None

    @property
    def vuelto(self) -> Decimal:
        if self.monto_recibido is None:
            return Decimal("0")
        exceso = self.monto_recibido - self.monto
        return exceso if exceso > 0 else Decimal("0")


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
    pagos: list[PagoVenta] = field(default_factory=list)
    motivo_anulacion: str | None = None
    created_at: datetime | None = None

    @property
    def anulada(self) -> bool:
        return self.estado == VENTA_ANULADA

    @property
    def vuelto(self) -> Decimal:
        return sum((p.vuelto for p in self.pagos), Decimal("0"))

    @property
    def total_efectivo(self) -> Decimal:
        """Cuánto de esta venta entró como dinero FÍSICO a la caja (para el arqueo)."""
        return sum((p.monto for p in self.pagos if p.es_efectivo), Decimal("0"))


@dataclass
class Anulacion:
    """El RASTRO de un reverso (RF-22): anulación total o devolución parcial.

    La venta original NUNCA se borra; cada reverso repone stock, registra cuánto
    dinero salió físicamente de la caja (efectivo_devuelto, en el turno en que
    ocurre) y queda visible para la administradora en su panel de caja.
    """

    id: int | None
    venta_id: int
    turno_id: int  # turno en el que se hizo el reverso (ajusta ESA caja)
    tipo: str  # ANULACION | DEVOLUCION
    usuario_id: int
    realizado_por: str  # snapshot del nombre
    motivo: str
    monto: Decimal  # valor de lo revertido
    efectivo_devuelto: Decimal  # cuánto salió del cajón (<= monto)
    items: list[dict]  # [{producto_id, nombre, cantidad}]
    created_at: datetime | None = None
