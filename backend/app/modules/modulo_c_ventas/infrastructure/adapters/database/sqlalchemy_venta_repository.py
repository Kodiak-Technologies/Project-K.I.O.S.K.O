# Adaptador: implementa VentaRepositoryPort usando SQLAlchemy.
from datetime import date, datetime, time, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.domain.entities import DetalleVenta, PagoVenta, Venta
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import (
    DetalleVentaModel,
    PagoVentaModel,
    VentaModel,
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

    async def listar(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        turno_id: int | None = None,
    ) -> list[Venta]:
        consulta = select(VentaModel).order_by(VentaModel.id.desc())
        if desde is not None:
            consulta = consulta.where(
                VentaModel.created_at >= datetime.combine(desde, time.min, tzinfo=timezone.utc)
            )
        if hasta is not None:
            consulta = consulta.where(
                VentaModel.created_at <= datetime.combine(hasta, time.max, tzinfo=timezone.utc)
            )
        if turno_id is not None:
            consulta = consulta.where(VentaModel.turno_id == turno_id)
        filas = (await self._db.execute(consulta)).scalars().all()
        return [_a_entidad(f) for f in filas]

    async def actualizar_estado(
        self, venta_id: int, estado: str, motivo: str | None = None
    ) -> None:
        valores: dict = {"estado": estado}
        if motivo is not None:
            valores["motivo_anulacion"] = motivo
        await self._db.execute(
            update(VentaModel).where(VentaModel.id == venta_id).values(**valores)
        )
