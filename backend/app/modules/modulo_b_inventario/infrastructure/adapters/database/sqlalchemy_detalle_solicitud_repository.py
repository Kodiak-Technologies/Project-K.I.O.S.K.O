# Adaptador: implementa DetalleSolicitudRepositoryPort usando SQLAlchemy async.
# Stub de PR1: la implementación real se hace en PR2.
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import DetalleSolicitud
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)


class SqlAlchemyDetalleSolicitudRepository(DetalleSolicitudRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear_bulk(self, detalles: list[DetalleSolicitud]) -> list[DetalleSolicitud]:
        raise NotImplementedError("Implementado en PR2")

    async def listar_por_solicitud(self, solicitud_id: int) -> list[DetalleSolicitud]:
        raise NotImplementedError("Implementado en PR2")

    async def eliminar_por_solicitud(self, solicitud_id: int) -> None:
        raise NotImplementedError("Implementado en PR2")
