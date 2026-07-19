# Adaptador: implementa MovimientoInventarioRepositoryPort usando SQLAlchemy async.
# Stub de PR1: la implementación real se hace en PR2.
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import MovimientoInventario
from app.modules.modulo_b_inventario.domain.ports.movimiento_inventario_repository_port import (
    MovimientoInventarioRepositoryPort,
)


class SqlAlchemyMovimientoInventarioRepository(MovimientoInventarioRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def append(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        raise NotImplementedError("Implementado en PR2")

    async def listar_paginado(
        self,
        *,
        producto_id=None,
        tipo=None,
        fecha_desde=None,
        fecha_hasta=None,
        page=1,
        page_size=20,
    ):
        raise NotImplementedError("Implementado en PR2")
