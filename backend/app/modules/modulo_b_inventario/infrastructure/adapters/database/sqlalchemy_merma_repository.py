# Adaptador: implementa MermaRepositoryPort usando SQLAlchemy async.
# Stub de PR1: la implementación real se hace en PR2.
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
    MermaRepositoryPort,
)


class SqlAlchemyMermaRepository(MermaRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, merma: Merma) -> Merma:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_id(self, merma_id: int) -> Merma | None:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_id_for_update(self, merma_id: int) -> Merma | None:
        raise NotImplementedError("Implementado en PR2")

    async def actualizar(self, merma: Merma) -> Merma:
        raise NotImplementedError("Implementado en PR2")

    async def listar_paginado(
        self,
        *,
        estado=None,
        motivo=None,
        producto_id=None,
        fecha_desde=None,
        fecha_hasta=None,
        page=1,
        page_size=20,
    ):
        raise NotImplementedError("Implementado en PR2")
