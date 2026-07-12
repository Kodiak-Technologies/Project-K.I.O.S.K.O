# Adaptador: implementa AuditoriaRepositoryPort usando SQLAlchemy async.
# Solo INSERT y SELECT: la bitácora es inmutable (trigger en BD lo refuerza).
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import RegistroAuditoria
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    BitacoraAuditoriaModel,
)


def _a_entidad(fila: BitacoraAuditoriaModel) -> RegistroAuditoria:
    return RegistroAuditoria(
        id=fila.id,
        usuario_id=fila.usuario_id,
        rol=fila.rol,
        accion=fila.accion,
        entidad=fila.entidad,
        entidad_id=fila.entidad_id,
        valor_anterior=fila.valor_anterior,
        valor_nuevo=fila.valor_nuevo,
        motivo=fila.motivo,
        ip=fila.ip,
        user_agent=fila.user_agent,
        created_at=fila.created_at,
    )


class SqlAlchemyAuditoriaRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def registrar(self, registro: RegistroAuditoria) -> RegistroAuditoria:
        fila = BitacoraAuditoriaModel(
            usuario_id=registro.usuario_id,
            rol=registro.rol,
            accion=registro.accion,
            entidad=registro.entidad,
            entidad_id=registro.entidad_id,
            valor_anterior=registro.valor_anterior,
            valor_nuevo=registro.valor_nuevo,
            motivo=registro.motivo,
            ip=registro.ip,
            user_agent=registro.user_agent,
        )
        self._db.add(fila)
        await self._db.flush()
        return _a_entidad(fila)

    async def consultar(
        self,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        usuario_id: int | None = None,
        accion: str | None = None,
        entidad: str | None = None,
        pagina: int = 1,
        tamano_pagina: int = 25,
    ) -> tuple[list[RegistroAuditoria], int]:
        filtros = []
        if desde is not None:
            filtros.append(BitacoraAuditoriaModel.created_at >= desde)
        if hasta is not None:
            filtros.append(BitacoraAuditoriaModel.created_at <= hasta)
        if usuario_id is not None:
            filtros.append(BitacoraAuditoriaModel.usuario_id == usuario_id)
        if accion is not None:
            filtros.append(BitacoraAuditoriaModel.accion == accion)
        if entidad is not None:
            filtros.append(BitacoraAuditoriaModel.entidad == entidad)

        total = (
            await self._db.execute(select(func.count()).select_from(BitacoraAuditoriaModel).where(*filtros))
        ).scalar_one()

        resultado = await self._db.execute(
            select(BitacoraAuditoriaModel)
            .where(*filtros)
            .order_by(BitacoraAuditoriaModel.created_at.desc())
            .offset((pagina - 1) * tamano_pagina)
            .limit(tamano_pagina)
        )
        return [_a_entidad(f) for f in resultado.scalars().all()], total
