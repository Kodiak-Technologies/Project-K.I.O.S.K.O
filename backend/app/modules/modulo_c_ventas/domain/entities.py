# Entidades de dominio: Venta, DetalleVenta, Caja, AperturaCaja, CierreCaja, MedioPago.
# Python puro: sin FastAPI ni SQLAlchemy.
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.modules.modulo_c_ventas.domain.value_objects import TURNO_ABIERTO


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
