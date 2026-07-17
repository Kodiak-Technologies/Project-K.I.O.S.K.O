# Adaptador: implementa CajaRepositoryPort usando SQLAlchemy.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.domain.entities import TurnoCaja
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import TURNO_ABIERTO
from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import TurnoCajaModel


def _a_entidad(fila: TurnoCajaModel) -> TurnoCaja:
    return TurnoCaja(
        id=fila.id,
        usuario_id=fila.usuario_id,
        abierto_por=fila.abierto_por,
        monto_inicial=fila.monto_inicial,
        estado=fila.estado,
        abierto_en=fila.abierto_en,
        cerrado_en=fila.cerrado_en,
        monto_final=fila.monto_final,
        usuario_cierre_id=fila.usuario_cierre_id,
        cerrado_por=fila.cerrado_por,
    )


class SqlAlchemyCajaRepository(CajaRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def turno_abierto(self) -> TurnoCaja | None:
        fila = (
            await self._db.execute(
                select(TurnoCajaModel).where(TurnoCajaModel.estado == TURNO_ABIERTO)
            )
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def buscar_por_id(self, turno_id: int) -> TurnoCaja | None:
        fila = (
            await self._db.execute(select(TurnoCajaModel).where(TurnoCajaModel.id == turno_id))
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def abrir(self, turno: TurnoCaja) -> TurnoCaja:
        fila = TurnoCajaModel(
            usuario_id=turno.usuario_id,
            abierto_por=turno.abierto_por,
            monto_inicial=turno.monto_inicial,
            estado=turno.estado,
        )
        self._db.add(fila)
        await self._db.flush()
        await self._db.refresh(fila)  # trae abierto_en generado por la BD
        return _a_entidad(fila)

    async def listar(self, limite: int = 30) -> list[TurnoCaja]:
        filas = (
            await self._db.execute(
                select(TurnoCajaModel).order_by(TurnoCajaModel.id.desc()).limit(limite)
            )
        ).scalars()
        return [_a_entidad(f) for f in filas]
