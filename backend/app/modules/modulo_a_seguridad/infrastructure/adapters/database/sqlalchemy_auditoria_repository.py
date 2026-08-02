# Adaptador: implementa AuditoriaRepositoryPort usando SQLAlchemy async.
# Solo INSERT y SELECT: la bitácora es inmutable (trigger en BD lo refuerza).
from datetime import datetime

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import RegistroAuditoria
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    BitacoraAuditoriaModel,
)


from decimal import Decimal
from typing import Any


def _sanitizar_json(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float, str, bool)):
        return val
    if isinstance(val, dict):
        return {str(k): _sanitizar_json(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_sanitizar_json(item) for item in val]
    return str(val)


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
            valor_anterior=_sanitizar_json(registro.valor_anterior),
            valor_nuevo=_sanitizar_json(registro.valor_nuevo),
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
        cursor: tuple[datetime, int] | None = None,
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

        consulta = (
            select(BitacoraAuditoriaModel)
            .where(*filtros)
            # El desempate por PK hace la paginación determinista: `created_at`
            # se repite (varios eventos en el mismo instante) y sin él el orden
            # entre empatados no está garantizado, así que una fila podía salir
            # en dos páginas y otra en ninguna.
            .order_by(
                BitacoraAuditoriaModel.created_at.desc(),
                BitacoraAuditoriaModel.id.desc(),
            )
            .limit(tamano_pagina)
        )
        if cursor is not None:
            # Keyset: "lo que viene después de esta fila". Inmune a las
            # inserciones de arriba, que en la bitácora son constantes.
            momento, ultimo_id = cursor
            consulta = consulta.where(
                tuple_(
                    BitacoraAuditoriaModel.created_at, BitacoraAuditoriaModel.id
                )
                < (momento, ultimo_id)
            )
        else:
            consulta = consulta.offset((pagina - 1) * tamano_pagina)

        resultado = await self._db.execute(consulta)
        return [_a_entidad(f) for f in resultado.scalars().all()], total
