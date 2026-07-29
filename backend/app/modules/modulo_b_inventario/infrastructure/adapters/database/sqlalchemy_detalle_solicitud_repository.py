# Adaptador: implementa DetalleSolicitudRepositoryPort usando SQLAlchemy async.
# Implementación completa de PR2.
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import DetalleSolicitud
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    DetalleSolicitudModel,
    ProductoModel,
)


def _a_entidad(
    fila: DetalleSolicitudModel,
    producto_nombre: str | None = None,
    producto_codigo: str | None = None,
) -> DetalleSolicitud:
    return DetalleSolicitud(
        id=fila.id,
        solicitud_id=fila.solicitud_id,
        producto_id=fila.producto_id,
        cantidad=fila.cantidad,
        precio_compra_total=fila.precio_compra_total,
        created_at=fila.created_at,
        producto_nombre=producto_nombre,
        producto_codigo=producto_codigo,
        nuevo_codigo=fila.nuevo_codigo,
        nuevo_nombre=fila.nuevo_nombre,
        nuevo_categoria_id=fila.nuevo_categoria_id,
        margen_ganancia=fila.margen_ganancia,
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
                precio_compra_total=d.precio_compra_total,
                nuevo_codigo=d.nuevo_codigo,
                nuevo_nombre=d.nuevo_nombre,
                nuevo_categoria_id=d.nuevo_categoria_id,
                margen_ganancia=d.margen_ganancia,
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
        # JOIN con productos: el nombre viaja en la respuesta para que el
        # cliente no tenga que cargar el catálogo entero y traducir el id.
        # OUTER: las líneas que proponen un producto nuevo todavía no tienen
        # `producto_id`, y con un INNER se caerían del listado.
        filas = (
            await self._db.execute(
                select(DetalleSolicitudModel, ProductoModel.nombre, ProductoModel.codigo)
                .outerjoin(
                    ProductoModel, DetalleSolicitudModel.producto_id == ProductoModel.id
                )
                .where(DetalleSolicitudModel.solicitud_id == solicitud_id)
                .order_by(DetalleSolicitudModel.id)
            )
        ).all()
        return [_a_entidad(f, nombre, codigo) for f, nombre, codigo in filas]

    async def asignar_producto(self, detalle_id: int, producto_id: int) -> None:
        await self._db.execute(
            update(DetalleSolicitudModel)
            .where(DetalleSolicitudModel.id == detalle_id)
            .values(producto_id=producto_id)
        )

    async def eliminar_por_solicitud(self, solicitud_id: int) -> None:
        # Solo usado en rollback manual. En BD ya hay ON DELETE CASCADE.
        await self._db.execute(
            DetalleSolicitudModel.__table__.delete().where(
                DetalleSolicitudModel.solicitud_id == solicitud_id
            )
        )
