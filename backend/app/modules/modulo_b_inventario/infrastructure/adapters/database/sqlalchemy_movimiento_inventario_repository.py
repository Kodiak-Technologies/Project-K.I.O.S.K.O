# Adaptador: implementa MovimientoInventarioRepositoryPort (append-only).
# Implementación completa de PR2.
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import MovimientoInventario
from app.modules.modulo_b_inventario.domain.ports.movimiento_inventario_repository_port import (
    MovimientoInventarioRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import TipoMovimiento
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    MovimientoInventarioModel,
    ProductoModel,
)


def _a_entidad(
    fila: MovimientoInventarioModel,
    producto_nombre: str | None = None,
    producto_codigo: str | None = None,
) -> MovimientoInventario:
    return MovimientoInventario(
        id=fila.id,
        producto_id=fila.producto_id,
        cantidad=fila.cantidad,
        tipo=TipoMovimiento(fila.tipo),
        registrado_por=fila.registrado_por,
        registrado_por_nombre=fila.registrado_por_nombre,
        motivo=fila.motivo,
        solicitud_ingreso_id=fila.solicitud_ingreso_id,
        merma_id=fila.merma_id,
        created_at=fila.created_at,
        producto_nombre=producto_nombre,
        producto_codigo=producto_codigo,
    )


class SqlAlchemyMovimientoInventarioRepository(MovimientoInventarioRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def append(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        fila = MovimientoInventarioModel(
            producto_id=movimiento.producto_id,
            cantidad=movimiento.cantidad,
            tipo=str(movimiento.tipo),
            motivo=movimiento.motivo,
            solicitud_ingreso_id=movimiento.solicitud_ingreso_id,
            merma_id=movimiento.merma_id,
            registrado_por=movimiento.registrado_por,
            registrado_por_nombre=movimiento.registrado_por_nombre,
        )
        self._db.add(fila)
        await self._db.flush()
        movimiento.id = fila.id
        movimiento.created_at = fila.created_at
        return movimiento

    async def listar_paginado(
        self,
        *,
        producto_id: int | None = None,
        tipo: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[MovimientoInventario], int]:
        filtros: list[Any] = []
        if producto_id is not None:
            filtros.append(MovimientoInventarioModel.producto_id == producto_id)
        if tipo is not None:
            filtros.append(MovimientoInventarioModel.tipo == tipo)
        if fecha_desde is not None:
            filtros.append(MovimientoInventarioModel.created_at >= fecha_desde)
        if fecha_hasta is not None:
            filtros.append(MovimientoInventarioModel.created_at <= fecha_hasta)

        total = (
            await self._db.execute(
                select(func.count())
                .select_from(MovimientoInventarioModel)
                .where(*filtros)
            )
        ).scalar_one()
        # JOIN con productos: ver nota en el repo de detalle_solicitud.
        consulta = (
            select(
                MovimientoInventarioModel,
                ProductoModel.nombre,
                ProductoModel.codigo,
            )
            .join(
                ProductoModel,
                MovimientoInventarioModel.producto_id == ProductoModel.id,
            )
            .where(*filtros)
            # Desempate por PK: sin él, los movimientos del mismo instante
            # (una venta escribe varias líneas a la vez) no tienen orden
            # garantizado y se repiten o se pierden entre páginas.
            .order_by(
                MovimientoInventarioModel.created_at.desc(),
                MovimientoInventarioModel.id.desc(),
            )
            .limit(page_size)
        )
        if cursor is not None:
            # Keyset: cada venta escribe movimientos nuevos por arriba, así que
            # con OFFSET las páginas se corren mientras el usuario navega.
            momento, ultimo_id = cursor
            consulta = consulta.where(
                tuple_(
                    MovimientoInventarioModel.created_at,
                    MovimientoInventarioModel.id,
                )
                < (momento, ultimo_id)
            )
        else:
            consulta = consulta.offset((page - 1) * page_size)

        filas = (await self._db.execute(consulta)).all()
        return [_a_entidad(f, nombre, codigo) for f, nombre, codigo in filas], total
