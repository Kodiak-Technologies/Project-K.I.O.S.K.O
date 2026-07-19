# Adaptador: implementa PagoProveedorRepositoryPort usando SQLAlchemy async.
# Stub de PR1: la implementación real se hace en PR2.
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import PagoProveedor
from app.modules.modulo_b_inventario.domain.ports.pago_proveedor_repository_port import (
    PagoProveedorRepositoryPort,
)


class SqlAlchemyPagoProveedorRepository(PagoProveedorRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, pago: PagoProveedor) -> PagoProveedor:
        raise NotImplementedError("Implementado en PR2")

    async def listar_por_proveedor(
        self,
        proveedor_id,
        *,
        tipo=None,
        fecha_desde=None,
        fecha_hasta=None,
        page=1,
        page_size=20,
    ):
        raise NotImplementedError("Implementado en PR2")

    async def sum_tipo(self, proveedor_id: int, tipo: str) -> Decimal:
        raise NotImplementedError("Implementado en PR2")
