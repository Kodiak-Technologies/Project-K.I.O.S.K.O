# Adaptador: implementa ProveedorRepositoryPort usando SQLAlchemy async.
# Implementación completa de PR2.
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import Proveedor
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    ProveedorModel,
)


def _a_entidad(fila: ProveedorModel) -> Proveedor:
    return Proveedor(
        id=fila.id,
        razon_social=fila.razon_social,
        creado_por=fila.creado_por,
        creado_por_nombre=fila.creado_por_nombre,
        ruc=fila.ruc,
        telefono=fila.telefono,
        email=fila.email,
        direccion=fila.direccion,
        activo=fila.activo,
        deuda_actual=fila.deuda_actual,
        created_at=fila.created_at,
        updated_at=fila.updated_at,
        deleted_at=fila.deleted_at,
        deleted_by=fila.deleted_by,
    )


class SqlAlchemyProveedorRepository(ProveedorRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, proveedor: Proveedor) -> Proveedor:
        fila = ProveedorModel(
            razon_social=proveedor.razon_social,
            ruc=proveedor.ruc,
            telefono=proveedor.telefono,
            email=proveedor.email,
            direccion=proveedor.direccion,
            activo=proveedor.activo,
            deuda_actual=proveedor.deuda_actual,
            creado_por=proveedor.creado_por,
            creado_por_nombre=proveedor.creado_por_nombre,
        )
        self._db.add(fila)
        await self._db.flush()
        return _a_entidad(fila)

    async def find_by_id(self, proveedor_id: int) -> Proveedor | None:
        fila = (
            await self._db.execute(
                select(ProveedorModel).where(ProveedorModel.id == proveedor_id)
            )
        ).scalar_one_or_none()
        if fila is None or fila.deleted_at is not None:
            return None
        return _a_entidad(fila)

    async def find_by_id_for_update(self, proveedor_id: int) -> Proveedor | None:
        fila = (
            await self._db.execute(
                select(ProveedorModel)
                .where(ProveedorModel.id == proveedor_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if fila is None or fila.deleted_at is not None:
            return None
        return _a_entidad(fila)

    async def actualizar(self, proveedor: Proveedor) -> Proveedor:
        from app.shared.kernel.exceptions import NoEncontradoError

        fila = (
            await self._db.execute(
                select(ProveedorModel).where(ProveedorModel.id == proveedor.id)
            )
        ).scalar_one_or_none()
        # `scalar_one()` levantaba NoResultFound (500) para un id inexistente.
        if fila is None or fila.deleted_at is not None:
            raise NoEncontradoError("Proveedor no encontrado.")
        fila.razon_social = proveedor.razon_social
        fila.ruc = proveedor.ruc
        fila.telefono = proveedor.telefono
        fila.email = proveedor.email
        fila.direccion = proveedor.direccion
        fila.activo = proveedor.activo
        await self._db.flush()
        # `updated_at` (onupdate=now()) queda expirado tras el flush: sin este
        # refresh, leerlo dispara MissingGreenlet (500).
        await self._db.refresh(fila)
        return _a_entidad(fila)

    async def listar_paginado(
        self,
        *,
        search: str | None = None,
        solo_con_deuda: bool = False,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Proveedor], int]:
        filtros: list[Any] = [ProveedorModel.deleted_at.is_(None)]
        if activo is not None:
            filtros.append(ProveedorModel.activo == activo)
        if solo_con_deuda:
            filtros.append(ProveedorModel.deuda_actual > 0)
        if search:
            patron = f"%{search.strip()}%"
            filtros.append(ProveedorModel.razon_social.ilike(patron))

        total = (
            await self._db.execute(
                select(func.count()).select_from(ProveedorModel).where(*filtros)
            )
        ).scalar_one()
        filas = (
            (
                await self._db.execute(
                    select(ProveedorModel)
                    .where(*filtros)
                    # Desempate por PK: dos proveedores pueden compartir razón
                    # social, y sin él la paginación no es determinista.
                    .order_by(ProveedorModel.razon_social, ProveedorModel.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return [_a_entidad(f) for f in filas], total

    async def find_by_ruc(self, ruc: str) -> Proveedor | None:
        fila = (
            await self._db.execute(
                select(ProveedorModel).where(
                    ProveedorModel.ruc == ruc,
                    ProveedorModel.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def incrementar_deuda_atomic(
        self, proveedor_id: int, delta: Decimal
    ) -> bool:
        from sqlalchemy import update

        # Garantiza que la deuda resultante no quede negativa
        resultado = await self._db.execute(
            update(ProveedorModel)
            .where(
                ProveedorModel.id == proveedor_id,
                ProveedorModel.deleted_at.is_(None),
                ProveedorModel.deuda_actual + delta >= 0,
            )
            .values(deuda_actual=ProveedorModel.deuda_actual + delta)
        )
        return (resultado.rowcount or 0) == 1
