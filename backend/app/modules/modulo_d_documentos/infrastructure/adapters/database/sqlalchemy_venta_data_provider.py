from datetime import datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.infrastructure.adapters.database.models import (
    VentaModel,
    DetalleVentaModel,
)


class SqlAlchemyVentaDataProvider:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def obtener_venta(self, venta_id: int) -> dict | None:
        fila = (
            await self._db.execute(select(VentaModel).where(VentaModel.id == venta_id))
        ).scalar_one_or_none()
        if fila is None:
            return None
        return {
            "id": fila.id,
            "total": float(fila.total),
            "metodo_pago": fila.metodo_pago,
            "estado": fila.estado,
            "vendedor": fila.vendedor,
            "fecha": fila.vendida_en or fila.created_at,
        }

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        consulta = select(VentaModel).order_by(VentaModel.id.desc())

        if desde:
            fecha_desde = datetime.fromisoformat(desde)
            consulta = consulta.where(
                VentaModel.created_at >= datetime.combine(fecha_desde.date(), time.min, tzinfo=timezone.utc)
            )
        if hasta:
            fecha_hasta = datetime.fromisoformat(hasta)
            consulta = consulta.where(
                VentaModel.created_at <= datetime.combine(fecha_hasta.date(), time.max, tzinfo=timezone.utc)
            )

        filas = (await self._db.execute(consulta)).scalars().all()
        return [
            {
                "id": f.id,
                "total": float(f.total),
                "metodo_pago": f.metodo_pago,
                "estado": f.estado,
                "vendedor": f.vendedor,
                "fecha": f.vendida_en or f.created_at,
            }
            for f in filas
        ]

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        filas = (
            await self._db.execute(
                select(DetalleVentaModel).where(DetalleVentaModel.venta_id == venta_id)
            )
        ).scalars().all()
        return [
            {
                "producto_id": d.producto_id,
                "nombre": d.nombre,
                "precio_unitario": float(d.precio_unitario),
                "cantidad": d.cantidad,
            }
            for d in filas
        ]
