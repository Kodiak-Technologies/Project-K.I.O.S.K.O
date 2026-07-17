# Adaptador: implementa MetodoPagoRepositoryPort usando SQLAlchemy.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.domain.entities import MetodoPago
from app.modules.modulo_c_ventas.domain.ports.metodo_pago_repository_port import (
    MetodoPagoRepositoryPort,
)
from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import MetodoPagoModel


def _a_entidad(fila: MetodoPagoModel) -> MetodoPago:
    return MetodoPago(
        id=fila.id, codigo=fila.codigo, nombre=fila.nombre,
        es_efectivo=fila.es_efectivo, activo=fila.activo,
    )


class SqlAlchemyMetodoPagoRepository(MetodoPagoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def listar(self, solo_activos: bool = True) -> list[MetodoPago]:
        consulta = select(MetodoPagoModel).order_by(MetodoPagoModel.id)
        if solo_activos:
            consulta = consulta.where(MetodoPagoModel.activo.is_(True))
        filas = (await self._db.execute(consulta)).scalars()
        return [_a_entidad(f) for f in filas]

    async def buscar_por_codigo(self, codigo: str) -> MetodoPago | None:
        fila = (
            await self._db.execute(
                select(MetodoPagoModel).where(MetodoPagoModel.codigo == codigo)
            )
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def crear(self, metodo: MetodoPago) -> MetodoPago:
        fila = MetodoPagoModel(
            codigo=metodo.codigo, nombre=metodo.nombre,
            es_efectivo=metodo.es_efectivo, activo=metodo.activo,
        )
        self._db.add(fila)
        await self._db.flush()
        return _a_entidad(fila)

    async def actualizar(self, metodo_id: int, cambios: dict) -> MetodoPago:
        fila = (
            await self._db.execute(select(MetodoPagoModel).where(MetodoPagoModel.id == metodo_id))
        ).scalar_one()
        for campo in ("nombre", "activo"):
            if campo in cambios and cambios[campo] is not None:
                setattr(fila, campo, cambios[campo])
        await self._db.flush()
        return _a_entidad(fila)
