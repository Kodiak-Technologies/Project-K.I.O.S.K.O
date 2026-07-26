# Adaptador: implementa VentaRepositoryPort usando SQLAlchemy.
from datetime import date, datetime, time, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config.zona_horaria import zona_negocio

from app.modules.modulo_c_ventas.domain.entities import Anulacion, DetalleVenta, PagoVenta, Venta
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import (
    AnulacionModel,
    DetalleVentaModel,
    PagoVentaModel,
    VentaModel,
)


def _anulacion_a_entidad(fila: AnulacionModel) -> Anulacion:
    return Anulacion(
        id=fila.id,
        venta_id=fila.venta_id,
        turno_id=fila.turno_id,
        tipo=fila.tipo,
        usuario_id=fila.usuario_id,
        realizado_por=fila.realizado_por,
        motivo=fila.motivo,
        monto=fila.monto,
        efectivo_devuelto=fila.efectivo_devuelto,
        items=fila.items or [],
        created_at=fila.created_at,
    )


def _a_entidad(fila: VentaModel) -> Venta:
    return Venta(
        id=fila.id,
        turno_id=fila.turno_id,
        usuario_id=fila.usuario_id,
        vendedor=fila.vendedor,
        total=fila.total,
        metodo_pago=fila.metodo_pago,
        estado=fila.estado,
        motivo_anulacion=fila.motivo_anulacion,
        client_uuid=fila.client_uuid,
        registrada_offline=fila.registrada_offline,
        vendida_en=fila.vendida_en,
        created_at=fila.created_at,
        detalles=[
            DetalleVenta(
                id=d.id,
                producto_id=d.producto_id,
                nombre=d.nombre,
                precio_unitario=d.precio_unitario,
                cantidad=d.cantidad,
                cantidad_devuelta=d.cantidad_devuelta,
            )
            for d in fila.detalles
        ],
        pagos=[
            PagoVenta(
                id=p.id,
                codigo_metodo=p.codigo_metodo,
                monto=p.monto,
                es_efectivo=p.es_efectivo,
                monto_recibido=p.monto_recibido,
                metodo_pago_id=p.metodo_pago_id,
            )
            for p in fila.pagos
        ],
    )


class SqlAlchemyVentaRepository(VentaRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, venta: Venta) -> Venta:
        fila = VentaModel(
            turno_id=venta.turno_id,
            usuario_id=venta.usuario_id,
            vendedor=venta.vendedor,
            total=venta.total,
            metodo_pago=venta.metodo_pago,
            estado=venta.estado,
            client_uuid=venta.client_uuid,
            registrada_offline=venta.registrada_offline,
            vendida_en=venta.vendida_en,
        )
        self._db.add(fila)
        await self._db.flush()
        for detalle in venta.detalles:
            self._db.add(
                DetalleVentaModel(
                    venta_id=fila.id,
                    producto_id=detalle.producto_id,
                    nombre=detalle.nombre,
                    precio_unitario=detalle.precio_unitario,
                    cantidad=detalle.cantidad,
                )
            )
        for pago in venta.pagos:
            self._db.add(
                PagoVentaModel(
                    venta_id=fila.id,
                    metodo_pago_id=pago.metodo_pago_id,
                    codigo_metodo=pago.codigo_metodo,
                    es_efectivo=pago.es_efectivo,
                    monto=pago.monto,
                    monto_recibido=pago.monto_recibido,
                )
            )
        await self._db.flush()
        return await self.buscar_por_id(fila.id)

    async def buscar_por_id(self, venta_id: int) -> Venta | None:
        fila = (
            await self._db.execute(select(VentaModel).where(VentaModel.id == venta_id))
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def buscar_por_uuid(self, client_uuid: str) -> Venta | None:
        fila = (
            await self._db.execute(
                select(VentaModel).where(VentaModel.client_uuid == client_uuid)
            )
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def listar(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        turno_id: int | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[Venta], int]:
        """Devuelve (ventas, total). Con `page`/`page_size` acota en SQL.

        El histórico crece sin techo: traerlo entero en cada consulta hacía que
        la pantalla acumulara miles de filas y el payload creciera para siempre.
        """
        # Los límites del rango se arman en la zona del NEGOCIO, no en UTC: si no,
        # una venta de las 23:55 en Lima cae en el día siguiente y "las ventas de
        # hoy" salen incompletas.
        zona = zona_negocio()
        filtros = []
        if desde is not None:
            filtros.append(
                VentaModel.created_at >= datetime.combine(desde, time.min, tzinfo=zona)
            )
        if hasta is not None:
            filtros.append(
                VentaModel.created_at <= datetime.combine(hasta, time.max, tzinfo=zona)
            )
        if turno_id is not None:
            filtros.append(VentaModel.turno_id == turno_id)

        total = (
            await self._db.execute(
                select(func.count()).select_from(VentaModel).where(*filtros)
            )
        ).scalar_one()

        consulta = select(VentaModel).where(*filtros).order_by(VentaModel.id.desc())
        if page is not None and page_size is not None:
            consulta = consulta.offset((page - 1) * page_size).limit(page_size)
        filas = (await self._db.execute(consulta)).scalars().all()
        return [_a_entidad(f) for f in filas], total

    async def actualizar_estado(
        self, venta_id: int, estado: str, motivo: str | None = None
    ) -> None:
        valores: dict = {"estado": estado}
        if motivo is not None:
            valores["motivo_anulacion"] = motivo
        await self._db.execute(
            update(VentaModel).where(VentaModel.id == venta_id).values(**valores)
        )

    async def registrar_devolucion_detalle(self, detalle_id: int, cantidad: int) -> None:
        await self._db.execute(
            update(DetalleVentaModel)
            .where(DetalleVentaModel.id == detalle_id)
            .values(cantidad_devuelta=DetalleVentaModel.cantidad_devuelta + cantidad)
        )

    async def crear_anulacion(self, anulacion: Anulacion) -> Anulacion:
        fila = AnulacionModel(
            venta_id=anulacion.venta_id,
            turno_id=anulacion.turno_id,
            tipo=anulacion.tipo,
            usuario_id=anulacion.usuario_id,
            realizado_por=anulacion.realizado_por,
            motivo=anulacion.motivo,
            monto=anulacion.monto,
            efectivo_devuelto=anulacion.efectivo_devuelto,
            items=anulacion.items,
        )
        self._db.add(fila)
        await self._db.flush()
        anulacion.id = fila.id
        anulacion.created_at = fila.created_at
        return anulacion

    async def anulaciones_de_venta(self, venta_id: int) -> list[Anulacion]:
        filas = (
            await self._db.execute(
                select(AnulacionModel)
                .where(AnulacionModel.venta_id == venta_id)
                .order_by(AnulacionModel.id)
            )
        ).scalars()
        return [_anulacion_a_entidad(f) for f in filas]

    async def anulaciones_de_turno(self, turno_id: int) -> list[Anulacion]:
        filas = (
            await self._db.execute(
                select(AnulacionModel)
                .where(AnulacionModel.turno_id == turno_id)
                .order_by(AnulacionModel.id.desc())
            )
        ).scalars()
        return [_anulacion_a_entidad(f) for f in filas]
