# Adaptador: implementa ProveedorRepositoryPort usando SQLAlchemy async.
# Stub de PR1: la implementación real se hace en PR2.
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import Proveedor
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)


class SqlAlchemyProveedorRepository(ProveedorRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, proveedor: Proveedor) -> Proveedor:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_id(self, proveedor_id: int) -> Proveedor | None:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_id_for_update(self, proveedor_id: int) -> Proveedor | None:
        raise NotImplementedError("Implementado en PR2")

    async def actualizar(self, proveedor: Proveedor) -> Proveedor:
        raise NotImplementedError("Implementado en PR2")

    async def listar_paginado(
        self, *, search=None, solo_con_deuda=False, activo=None, page=1, page_size=20
    ):
        raise NotImplementedError("Implementado en PR2")

    async def find_by_ruc(self, ruc: str) -> Proveedor | None:
        raise NotImplementedError("Implementado en PR2")

    async def incrementar_deuda_atomic(
        self, proveedor_id: int, delta: Decimal
    ) -> bool:
        raise NotImplementedError("Implementado en PR2")
