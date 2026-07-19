from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.domain.entities import Respaldo
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import RespaldoModel


def _a_entidad(fila: RespaldoModel) -> Respaldo:
    return Respaldo(
        id=fila.id,
        archivo_nombre=fila.archivo_nombre,
        tamano_bytes=fila.tamano_bytes,
        estado=fila.estado,
        generado_en=fila.generado_en,
        expira_en=fila.expira_en,
    )


class SqlAlchemyRespaldoRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, respaldo: Respaldo) -> Respaldo:
        fila = RespaldoModel(
            archivo_nombre=respaldo.archivo_nombre,
            tamano_bytes=respaldo.tamano_bytes,
            estado=respaldo.estado,
            expira_en=respaldo.expira_en,
        )
        self._db.add(fila)
        await self._db.flush()
        await self._db.refresh(fila)
        return _a_entidad(fila)

    async def listar(self) -> list[Respaldo]:
        resultado = await self._db.execute(
            select(RespaldoModel).order_by(RespaldoModel.generado_en.desc())
        )
        return [_a_entidad(fila) for fila in resultado.scalars().all()]

    async def buscar_por_id(self, respaldo_id: int) -> Respaldo | None:
        resultado = await self._db.execute(
            select(RespaldoModel).where(RespaldoModel.id == respaldo_id)
        )
        fila = resultado.scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def actualizar(self, respaldo: Respaldo) -> Respaldo:
        resultado = await self._db.execute(
            select(RespaldoModel).where(RespaldoModel.id == respaldo.id)
        )
        fila = resultado.scalar_one_or_none()
        if fila is None:
            raise ValueError(f"Respaldo #{respaldo.id} no encontrado")
        fila.estado = respaldo.estado
        fila.tamano_bytes = respaldo.tamano_bytes
        fila.expira_en = respaldo.expira_en
        await self._db.flush()
        await self._db.refresh(fila)
        return _a_entidad(fila)

    async def eliminar_expirados(self) -> int:
        ahora = datetime.now(timezone.utc)
        resultado = await self._db.execute(
            delete(RespaldoModel).where(RespaldoModel.expira_en < ahora)
        )
        return resultado.rowcount
