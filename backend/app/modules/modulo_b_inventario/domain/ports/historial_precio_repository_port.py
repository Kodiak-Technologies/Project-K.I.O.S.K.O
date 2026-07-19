# Puerto: bitácora append-only de cambios de precio (HU-B11, D-06).
# El trigger BD `trg_historial_precios_no_update` rechaza UPDATE/DELETE.
# El adaptador NO expone actualizar/eliminar.
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import HistorialPrecio


class HistorialPrecioRepositoryPort(ABC):
    @abstractmethod
    async def append(self, historial: HistorialPrecio) -> HistorialPrecio:
        """Inserta una fila nueva. Nunca UPDATE."""

    @abstractmethod
    async def listar_por_producto(
        self,
        producto_id: int,
        *,
        tipo: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[HistorialPrecio], int]:
        """Devuelve (items, total) ordenado por created_at DESC."""
