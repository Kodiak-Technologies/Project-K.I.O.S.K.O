# Adaptador: implementa MermaRepositoryPort usando SQLAlchemy async.
# Implementación completa de PR2.
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
    MermaRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import EstadoMerma, MotivoMerma
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    MermaModel,
)


def _a_entidad(fila: MermaModel) -> Merma:
    return Merma(
        id=fila.id,
        producto_id=fila.producto_id,
        cantidad=fila.cantidad,
        motivo=MotivoMerma(fila.motivo),
        registrado_por=fila.registrado_por,
        registrado_por_nombre=fila.registrado_por_nombre,
        estado=EstadoMerma(fila.estado),
        observacion=fila.observacion,
        proveedor_id=fila.proveedor_id,
        motivo_rechazo=fila.motivo_rechazo,
        confirmado_por=fila.confirmado_por,
        confirmado_por_nombre=fila.confirmado_por_nombre,
        confirmado_en=fila.confirmado_en,
        rechazado_por=fila.rechazado_por,
        rechazado_por_nombre=fila.rechazado_por_nombre,
        rechazado_en=fila.rechazado_en,
        editado_por=fila.editado_por,
        editado_por_nombre=fila.editado_por_nombre,
        editado_en=fila.editado_en,
        created_at=fila.created_at,
        deleted_at=fila.deleted_at,
        deleted_by=fila.deleted_by,
    )


class SqlAlchemyMermaRepository(MermaRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, merma: Merma) -> Merma:
        fila = MermaModel(
            producto_id=merma.producto_id,
            cantidad=merma.cantidad,
            motivo=str(merma.motivo),
            observacion=merma.observacion,
            proveedor_id=merma.proveedor_id,
            estado=str(merma.estado),
            registrado_por=merma.registrado_por,
            registrado_por_nombre=merma.registrado_por_nombre,
        )
        self._db.add(fila)
        await self._db.flush()
        return _a_entidad(fila)

    async def find_by_id(self, merma_id: int) -> Merma | None:
        fila = (
            await self._db.execute(
                select(MermaModel).where(MermaModel.id == merma_id)
            )
        ).scalar_one_or_none()
        if fila is None or fila.deleted_at is not None:
            return None
        return _a_entidad(fila)

    async def find_by_id_for_update(self, merma_id: int) -> Merma | None:
        fila = (
            await self._db.execute(
                select(MermaModel)
                .where(MermaModel.id == merma_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if fila is None or fila.deleted_at is not None:
            return None
        return _a_entidad(fila)

    async def actualizar(self, merma: Merma) -> Merma:
        fila = (
            await self._db.execute(
                select(MermaModel).where(MermaModel.id == merma.id)
            )
        ).scalar_one()
        fila.estado = str(merma.estado)
        fila.motivo_rechazo = merma.motivo_rechazo
        fila.confirmado_por = merma.confirmado_por
        fila.confirmado_por_nombre = merma.confirmado_por_nombre
        fila.confirmado_en = merma.confirmado_en
        fila.rechazado_por = merma.rechazado_por
        fila.rechazado_por_nombre = merma.rechazado_por_nombre
        fila.rechazado_en = merma.rechazado_en
        await self._db.flush()
        return _a_entidad(fila)

    async def actualizar_cabecera(self, merma_id: int, cambios: dict) -> Merma:
        """sdd/modulo-b-aprobaciones-detalle-editar: PATCH parcial sobre la cabecera."""
        # Nota: la entidad Merma no tiene `updated_at`, pero la BD sí (o lo tendrá
        # tras la migración). Enviamos el campo solo si existe; confiamos en
        # que la entidad está en estado Registrada, así que el CHECK
        # chk_mermas_estado_consistente sigue satisfecho.
        await self._db.execute(
            MermaModel.__table__.update()
            .where(MermaModel.id == merma_id)
            .values(**cambios)
        )
        await self._db.flush()
        fila = (
            await self._db.execute(
                select(MermaModel).where(MermaModel.id == merma_id)
            )
        ).scalar_one()
        return _a_entidad(fila)

    async def listar_paginado(
        self,
        *,
        estado: str | None = None,
        motivo: str | None = None,
        producto_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Merma], int]:
        filtros: list[Any] = [MermaModel.deleted_at.is_(None)]
        if estado is not None:
            filtros.append(MermaModel.estado == estado)
        if motivo is not None:
            filtros.append(MermaModel.motivo == motivo)
        if producto_id is not None:
            filtros.append(MermaModel.producto_id == producto_id)
        if fecha_desde is not None:
            filtros.append(MermaModel.created_at >= fecha_desde)
        if fecha_hasta is not None:
            filtros.append(MermaModel.created_at <= fecha_hasta)

        total = (
            await self._db.execute(
                select(func.count()).select_from(MermaModel).where(*filtros)
            )
        ).scalar_one()
        filas = (
            (
                await self._db.execute(
                    select(MermaModel)
                    .where(*filtros)
                    .order_by(MermaModel.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return [_a_entidad(f) for f in filas], total
