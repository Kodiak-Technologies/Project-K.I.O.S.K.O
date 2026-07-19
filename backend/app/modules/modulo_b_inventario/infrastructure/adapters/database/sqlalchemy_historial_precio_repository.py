# Adaptador: implementa HistorialPrecioRepositoryPort usando SQLAlchemy async.
# Stub de PR1: la implementación real se hace en PR2.
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import HistorialPrecio
from app.modules.modulo_b_inventario.domain.ports.historial_precio_repository_port import (
    HistorialPrecioRepositoryPort,
)


class SqlAlchemyHistorialPrecioRepository(HistorialPrecioRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def append(self, historial: HistorialPrecio) -> HistorialPrecio:
        raise NotImplementedError("Implementado en PR2")

    async def listar_por_producto(
        self, producto_id, *, tipo=None, page=1, page_size=20
    ):
        raise NotImplementedError("Implementado en PR2")
