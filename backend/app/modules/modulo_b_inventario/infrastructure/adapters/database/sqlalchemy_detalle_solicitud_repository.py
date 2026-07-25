# Adaptador: implementa DetalleSolicitudRepositoryPort usando SQLAlchemy async.
# Implementación completa de PR2.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import DetalleSolicitud
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    DetalleSolicitudModel,
)


def _a_entidad(fila: DetalleSolicitudModel) -> DetalleSolicitud:
    return DetalleSolicitud(
        id=fila.id,
        solicitud_id=fila.solicitud_id,
        producto_id=fila.producto_id,
        cantidad=fila.cantidad,
        precio_compra_unitario=fila.precio_compra_unitario,
        created_at=fila.created_at,
    )


class SqlAlchemyDetalleSolicitudRepository(DetalleSolicitudRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear_bulk(
        self, detalles: list[DetalleSolicitud]
    ) -> list[DetalleSolicitud]:
        filas = [
            DetalleSolicitudModel(
                solicitud_id=d.solicitud_id,
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_compra_unitario=d.precio_compra_unitario,
            )
            for d in detalles
        ]
        self._db.add_all(filas)
        await self._db.flush()
        for d, fila in zip(detalles, filas):
            d.id = fila.id
            d.created_at = fila.created_at
        return detalles

    async def listar_por_solicitud(self, solicitud_id: int) -> list[DetalleSolicitud]:
        filas = (
            await self._db.execute(
                select(DetalleSolicitudModel)
                .where(DetalleSolicitudModel.solicitud_id == solicitud_id)
                .order_by(DetalleSolicitudModel.id)
            )
        ).scalars()
        return [_a_entidad(f) for f in filas]

    async def eliminar_por_solicitud(self, solicitud_id: int) -> None:
        # Solo usado en rollback manual. En BD ya hay ON DELETE CASCADE.
        await self._db.execute(
            DetalleSolicitudModel.__table__.delete().where(
                DetalleSolicitudModel.solicitud_id == solicitud_id
            )
        )
