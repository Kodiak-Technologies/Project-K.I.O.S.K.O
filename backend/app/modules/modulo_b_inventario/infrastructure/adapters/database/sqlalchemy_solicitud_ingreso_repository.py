# Adaptador: implementa SolicitudIngresoRepositoryPort usando SQLAlchemy async.
# Stub de PR1: la implementación real se hace en PR2.
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import SolicitudIngreso
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)


class SqlAlchemySolicitudIngresoRepository(SolicitudIngresoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_id(self, solicitud_id: int) -> SolicitudIngreso | None:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_id_for_update(self, solicitud_id: int) -> SolicitudIngreso | None:
        raise NotImplementedError("Implementado en PR2")

    async def actualizar(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        raise NotImplementedError("Implementado en PR2")

    async def listar_paginado(
        self,
        *,
        estado=None,
        proveedor_id=None,
        fecha_desde=None,
        fecha_hasta=None,
        page=1,
        page_size=20,
    ):
        raise NotImplementedError("Implementado en PR2")

    async def listar_por_solicitante(
        self, usuario_id, *, estado=None, page=1, page_size=20
    ):
        raise NotImplementedError("Implementado en PR2")
