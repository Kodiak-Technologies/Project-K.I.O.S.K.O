# Adaptador: implementa HistorialPrecioRepositoryPort (append-only).
# El trigger `trg_historial_precios_no_update` en BD rechaza UPDATE/DELETE.
# Implementación completa de PR2.
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import HistorialPrecio
from app.modules.modulo_b_inventario.domain.ports.historial_precio_repository_port import (
    HistorialPrecioRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import TipoPrecio
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    HistorialPrecioModel,
)


def _a_entidad(fila: HistorialPrecioModel) -> HistorialPrecio:
    return HistorialPrecio(
        id=fila.id,
        producto_id=fila.producto_id,
        precio_nuevo=fila.precio_nuevo,
        tipo_precio=TipoPrecio(fila.tipo_precio),
        modificado_por=fila.modificado_por,
        modificado_por_nombre=fila.modificado_por_nombre,
        precio_anterior=fila.precio_anterior,
        created_at=fila.created_at,
    )


class SqlAlchemyHistorialPrecioRepository(HistorialPrecioRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def append(self, historial: HistorialPrecio) -> HistorialPrecio:
        fila = HistorialPrecioModel(
            producto_id=historial.producto_id,
            precio_anterior=historial.precio_anterior,
            precio_nuevo=historial.precio_nuevo,
            tipo_precio=str(historial.tipo_precio),
            modificado_por=historial.modificado_por,
            modificado_por_nombre=historial.modificado_por_nombre,
        )
        self._db.add(fila)
        await self._db.flush()
        historial.id = fila.id
        historial.created_at = fila.created_at
        return historial

    async def listar_por_producto(
        self,
        producto_id: int,
        *,
        tipo: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[HistorialPrecio], int]:
        filtros: list[Any] = [HistorialPrecioModel.producto_id == producto_id]
        if tipo is not None:
            filtros.append(HistorialPrecioModel.tipo_precio == tipo)

        total = (
            await self._db.execute(
                select(func.count())
                .select_from(HistorialPrecioModel)
                .where(*filtros)
            )
        ).scalar_one()
        filas = (
            (
                await self._db.execute(
                    select(HistorialPrecioModel)
                    .where(*filtros)
                    .order_by(HistorialPrecioModel.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return [_a_entidad(f) for f in filas], total
