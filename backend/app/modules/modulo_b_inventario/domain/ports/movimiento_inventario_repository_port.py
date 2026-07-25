# Puerto: bitácora append-only de movimientos de inventario (RF-08, D-07).
# El adaptador NO expone actualizar/eliminar: las filas solo se insertan.
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import MovimientoInventario


class MovimientoInventarioRepositoryPort(ABC):
    @abstractmethod
    async def append(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        """Inserta en la bitácora. Convencionalmente append-only."""

    @abstractmethod
    async def listar_paginado(
        self,
        *,
        producto_id: int | None = None,
        tipo: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MovimientoInventario], int]:
        """Devuelve (items, total) ordenado por created_at DESC."""
