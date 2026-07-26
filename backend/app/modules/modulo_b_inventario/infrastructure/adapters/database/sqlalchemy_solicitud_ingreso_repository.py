# Adaptador: implementa SolicitudIngresoRepositoryPort usando SQLAlchemy async.
# Implementación completa de PR2.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.modulo_b_inventario.domain.entities import (
    DetalleSolicitud,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    DetalleSolicitudModel,
    ProductoModel,
    SolicitudIngresoModel,
)


def _a_entidad(
    fila: SolicitudIngresoModel, lineas: list[DetalleSolicitud] | None = None
) -> SolicitudIngreso:
    from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud

    return SolicitudIngreso(
        id=fila.id,
        estado=EstadoSolicitud(fila.estado),
        foto_boleta_url=fila.foto_boleta_url,
        solicitado_por=fila.solicitado_por,
        solicitado_por_nombre=fila.solicitado_por_nombre,
        proveedor_id=fila.proveedor_id,
        motivo_rechazo=fila.motivo_rechazo,
        revisado_por=fila.revisado_por,
        revisado_por_nombre=fila.revisado_por_nombre,
        revisado_en=fila.revisado_en,
        lineas=lineas or [],
        created_at=fila.created_at,
        updated_at=fila.updated_at,
        motivo=fila.motivo,
        editado_por=fila.editado_por,
        editado_por_nombre=fila.editado_por_nombre,
        editado_en=fila.editado_en,
        deleted_at=fila.deleted_at,
        deleted_by=fila.deleted_by,
    )


class SqlAlchemySolicitudIngresoRepository(SolicitudIngresoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def _lineas_de(
        self, solicitud_ids: list[int]
    ) -> dict[int, list[DetalleSolicitud]]:
        """Líneas de las solicitudes pedidas, con nombre y código del producto.

        El JOIN evita que el cliente tenga que cargar el catálogo entero solo
        para traducir `producto_id` a un nombre.
        """
        por_solicitud: dict[int, list[DetalleSolicitud]] = {}
        if not solicitud_ids:
            return por_solicitud
        filas = (
            await self._db.execute(
                select(DetalleSolicitudModel, ProductoModel.nombre, ProductoModel.codigo)
                .join(
                    ProductoModel,
                    DetalleSolicitudModel.producto_id == ProductoModel.id,
                )
                .where(DetalleSolicitudModel.solicitud_id.in_(solicitud_ids))
                .order_by(DetalleSolicitudModel.solicitud_id, DetalleSolicitudModel.id)
            )
        ).all()
        for linea, nombre, codigo in filas:
            por_solicitud.setdefault(linea.solicitud_id, []).append(
                DetalleSolicitud(
                    id=linea.id,
                    solicitud_id=linea.solicitud_id,
                    producto_id=linea.producto_id,
                    cantidad=linea.cantidad,
                    precio_compra_unitario=linea.precio_compra_unitario,
                    created_at=linea.created_at,
                    producto_nombre=nombre,
                    producto_codigo=codigo,
                )
            )
        return por_solicitud

    async def crear(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        fila = SolicitudIngresoModel(
            proveedor_id=solicitud.proveedor_id,
            estado=str(solicitud.estado),
            foto_boleta_url=solicitud.foto_boleta_url,
            motivo_rechazo=solicitud.motivo_rechazo,
            solicitado_por=solicitud.solicitado_por,
            solicitado_por_nombre=solicitud.solicitado_por_nombre,
        )
        self._db.add(fila)
        await self._db.flush()
        return await self.find_by_id(fila.id)  # type: ignore[arg-type, return-value]

    async def find_by_id(self, solicitud_id: int) -> SolicitudIngreso | None:
        fila = (
            await self._db.execute(
                select(SolicitudIngresoModel)
                .where(SolicitudIngresoModel.id == solicitud_id)
            )
        ).scalar_one_or_none()
        if fila is None or fila.deleted_at is not None:
            return None
        # Cargar líneas por separado
        lineas = (await self._lineas_de([solicitud_id])).get(solicitud_id, [])
        return _a_entidad(fila, lineas)

    async def find_by_id_for_update(
        self, solicitud_id: int
    ) -> SolicitudIngreso | None:
        fila = (
            await self._db.execute(
                select(SolicitudIngresoModel)
                .where(SolicitudIngresoModel.id == solicitud_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if fila is None or fila.deleted_at is not None:
            return None
        lineas = (await self._lineas_de([solicitud_id])).get(solicitud_id, [])
        return _a_entidad(fila, lineas)

    async def actualizar(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        fila = (
            await self._db.execute(
                select(SolicitudIngresoModel)
                .where(SolicitudIngresoModel.id == solicitud.id)
            )
        ).scalar_one()
        fila.estado = str(solicitud.estado)
        fila.motivo_rechazo = solicitud.motivo_rechazo
        fila.revisado_por = solicitud.revisado_por
        fila.revisado_por_nombre = solicitud.revisado_por_nombre
        fila.revisado_en = solicitud.revisado_en
        await self._db.flush()
        return await self.find_by_id(solicitud.id)  # type: ignore[arg-type, return-value]

    async def actualizar_cabecera(
        self, solicitud_id: int, cambios: dict
    ) -> SolicitudIngreso:
        """sdd/modulo-b-aprobaciones-detalle-editar: PATCH parcial sobre la cabecera.

        Escribe SOLO los campos provistos en `cambios` (no toca lineas, estado,
        ni los snapshots del revisor). Devuelve la entidad refrescada con sus
        lineas actuales.
        """
        from datetime import datetime, timezone

        # Defensa en profundidad: el server-side siempre pone updated_at.
        payload = dict(cambios)
        payload.setdefault("updated_at", datetime.now(timezone.utc))
        await self._db.execute(
            SolicitudIngresoModel.__table__.update()
            .where(SolicitudIngresoModel.id == solicitud_id)
            .values(**payload)
        )
        await self._db.flush()
        return await self.find_by_id(solicitud_id)  # type: ignore[return-value]

    async def listar_paginado(
        self,
        *,
        estado: str | None = None,
        proveedor_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[SolicitudIngreso], int]:
        return await self._listar(
            estado=estado,
            proveedor_id=proveedor_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            solicitado_por=None,
            page=page,
            page_size=page_size,
            cursor=cursor,
        )

    async def listar_por_solicitante(
        self,
        usuario_id: int,
        *,
        estado: str | None = None,
        proveedor_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[SolicitudIngreso], int]:
        # Los filtros de proveedor/fecha antes se descartaban para el CAJERO:
        # la API respondía 200 con la lista SIN filtrar.
        return await self._listar(
            estado=estado,
            proveedor_id=proveedor_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            solicitado_por=usuario_id,
            page=page,
            page_size=page_size,
            cursor=cursor,
        )

    async def _listar(
        self,
        *,
        estado: str | None,
        proveedor_id: int | None,
        fecha_desde: str | None,
        fecha_hasta: str | None,
        solicitado_por: int | None,
        page: int,
        page_size: int,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[SolicitudIngreso], int]:
        filtros: list[Any] = [SolicitudIngresoModel.deleted_at.is_(None)]
        if estado is not None:
            filtros.append(SolicitudIngresoModel.estado == estado)
        if proveedor_id is not None:
            filtros.append(SolicitudIngresoModel.proveedor_id == proveedor_id)
        if solicitado_por is not None:
            filtros.append(SolicitudIngresoModel.solicitado_por == solicitado_por)
        if fecha_desde is not None:
            filtros.append(SolicitudIngresoModel.created_at >= fecha_desde)
        if fecha_hasta is not None:
            filtros.append(SolicitudIngresoModel.created_at <= fecha_hasta)

        total = (
            await self._db.execute(
                select(func.count()).select_from(SolicitudIngresoModel).where(*filtros)
            )
        ).scalar_one()

        consulta = (
            select(SolicitudIngresoModel)
            .where(*filtros)
            # Desempate por PK para que la paginación sea determinista.
            .order_by(
                SolicitudIngresoModel.created_at.desc(),
                SolicitudIngresoModel.id.desc(),
            )
            .limit(page_size)
        )
        if cursor is not None:
            # Keyset: los cajeros registran ingresos mientras la administradora
            # revisa la cola, y con OFFSET eso le corría las páginas.
            momento, ultimo_id = cursor
            consulta = consulta.where(
                tuple_(
                    SolicitudIngresoModel.created_at, SolicitudIngresoModel.id
                )
                < (momento, ultimo_id)
            )
        else:
            consulta = consulta.offset((page - 1) * page_size)

        filas = (await self._db.execute(consulta)).scalars().all()
        # Cargar líneas en bloque (una sola consulta para toda la página)
        lineas_por_solicitud = await self._lineas_de([f.id for f in filas])
        return (
            [_a_entidad(f, lineas_por_solicitud.get(f.id, [])) for f in filas],
            total,
        )
