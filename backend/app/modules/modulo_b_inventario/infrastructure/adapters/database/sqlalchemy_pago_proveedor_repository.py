# Adaptador: implementa PagoProveedorRepositoryPort usando SQLAlchemy async.
# Implementación completa de PR2.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import PagoProveedor
from app.modules.modulo_b_inventario.domain.ports.pago_proveedor_repository_port import (
    PagoProveedorRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import TipoPago
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    PagoProveedorModel,
)


def _a_entidad(fila: PagoProveedorModel) -> PagoProveedor:
    return PagoProveedor(
        id=fila.id,
        proveedor_id=fila.proveedor_id,
        tipo=TipoPago(fila.tipo),
        monto=fila.monto,
        fecha=fila.fecha,
        registrado_por=fila.registrado_por,
        registrado_por_nombre=fila.registrado_por_nombre,
        concepto=fila.concepto,
        solicitud_ingreso_id=fila.solicitud_ingreso_id,
        created_at=fila.created_at,
        deleted_at=fila.deleted_at,
        deleted_by=fila.deleted_by,
    )


class SqlAlchemyPagoProveedorRepository(PagoProveedorRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, pago: PagoProveedor) -> PagoProveedor:
        fila = PagoProveedorModel(
            proveedor_id=pago.proveedor_id,
            tipo=str(pago.tipo),
            monto=pago.monto,
            fecha=pago.fecha,
            concepto=pago.concepto,
            solicitud_ingreso_id=pago.solicitud_ingreso_id,
            registrado_por=pago.registrado_por,
            registrado_por_nombre=pago.registrado_por_nombre,
        )
        self._db.add(fila)
        await self._db.flush()
        pago.id = fila.id
        pago.created_at = fila.created_at
        return pago

    async def listar_por_proveedor(
        self,
        proveedor_id: int,
        *,
        tipo: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PagoProveedor], int]:
        filtros: list[Any] = [
            PagoProveedorModel.proveedor_id == proveedor_id,
            PagoProveedorModel.deleted_at.is_(None),
        ]
        if tipo is not None:
            filtros.append(PagoProveedorModel.tipo == tipo)
        if fecha_desde is not None:
            filtros.append(PagoProveedorModel.fecha >= fecha_desde)
        if fecha_hasta is not None:
            filtros.append(PagoProveedorModel.fecha <= fecha_hasta)

        total = (
            await self._db.execute(
                select(func.count())
                .select_from(PagoProveedorModel)
                .where(*filtros)
            )
        ).scalar_one()
        filas = (
            (
                await self._db.execute(
                    select(PagoProveedorModel)
                    .where(*filtros)
                    # `fecha` es un día y varios pagos caen en el mismo: el
                    # desempate por PK hace la paginación determinista.
                    .order_by(
                        PagoProveedorModel.fecha.desc(),
                        PagoProveedorModel.created_at.desc(),
                        PagoProveedorModel.id.desc(),
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return [_a_entidad(f) for f in filas], total

    async def sum_tipo(self, proveedor_id: int, tipo: str) -> Decimal:
        from sqlalchemy import case

        # Solo aplica a no soft-deleted
        resultado = (
            await self._db.execute(
                select(func.coalesce(func.sum(PagoProveedorModel.monto), 0))
                .where(
                    PagoProveedorModel.proveedor_id == proveedor_id,
                    PagoProveedorModel.tipo == tipo,
                    PagoProveedorModel.deleted_at.is_(None),
                )
            )
        ).scalar_one()
        return Decimal(str(resultado))
