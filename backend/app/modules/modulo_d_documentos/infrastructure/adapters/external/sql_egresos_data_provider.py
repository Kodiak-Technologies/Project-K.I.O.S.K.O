# Adaptador: egresos reales del negocio para los reportes.
#
# El egreso NO se carga a mano: sale del costo de la mercadería que efectivamente
# entró al inventario, es decir de las líneas (`detalle_solicitud`) de las
# solicitudes de ingreso APROBADAS —cantidad × precio de compra unitario—.
# Una solicitud pendiente o rechazada no movió stock ni plata, así que no cuenta.
#
# Se fecha por `revisado_en` (cuándo se aprobó), que es el momento en que el
# costo impacta: es lo que hace comparable el reporte con las ventas del período.
# El día se calcula en la zona del NEGOCIO (`settings.zona_horaria_negocio`): un
# ingreso aprobado 23:55 en Lima pertenece a ese día, no al siguiente en UTC.
#
# Acceso por SQL directo a tablas del Módulo B, con la misma justificación
# documentada que usa el Módulo C para `productos` (ver ARQUITECTURA.md §4):
# es una lectura para reportes, no lógica de negocio duplicada.
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config.settings import settings
from app.shared.kernel.exceptions import ValidacionError


def _a_fecha(valor: str, campo: str) -> date:
    """asyncpg exige un `date` real: si le llega el string, revienta con 500."""
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        raise ValidacionError(f"{campo} debe tener formato YYYY-MM-DD.")


class SqlEgresosDataProvider:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def obtener_egresos(self, desde: str, hasta: str) -> list[dict]:
        """Un egreso por solicitud de ingreso aprobada dentro del rango."""
        filas = (
            await self._db.execute(
                text(
                    """
                    SELECT s.id,
                           (s.revisado_en AT TIME ZONE :tz)::date AS fecha,
                           p.razon_social                AS proveedor,
                           SUM(d.precio_compra_total)    AS monto,
                           SUM(d.cantidad)               AS unidades
                    FROM solicitudes_ingreso s
                    JOIN detalle_solicitud d ON d.solicitud_id = s.id
                    LEFT JOIN proveedores p  ON p.id = s.proveedor_id
                    WHERE s.estado = 'Aprobada'
                      AND s.deleted_at IS NULL
                      AND (s.revisado_en AT TIME ZONE :tz)::date BETWEEN :desde AND :hasta
                    GROUP BY s.id, s.revisado_en, p.razon_social
                    ORDER BY s.revisado_en DESC
                    """
                ),
                {
                    "desde": _a_fecha(desde, "desde"),
                    "hasta": _a_fecha(hasta, "hasta"),
                    "tz": settings.zona_horaria_negocio,
                },
            )
        ).all()
        return [
            {
                "concepto": (
                    f"Ingreso de mercadería #{fila.id}"
                    + (f" — {fila.proveedor}" if fila.proveedor else "")
                ),
                "monto": float(fila.monto or 0),
                "fecha": fila.fecha.isoformat() if fila.fecha else "",
                "unidades": int(fila.unidades or 0),
                # El pago al proveedor puede ser al contado o a crédito; el
                # reporte informa el COSTO de la mercadería, no la forma de pago.
                "metodo_pago": "",
            }
            for fila in filas
        ]

    async def total_egresos(self, desde: str, hasta: str) -> float:
        total = (
            await self._db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(d.precio_compra_total), 0)
                    FROM solicitudes_ingreso s
                    JOIN detalle_solicitud d ON d.solicitud_id = s.id
                    WHERE s.estado = 'Aprobada'
                      AND s.deleted_at IS NULL
                      AND (s.revisado_en AT TIME ZONE :tz)::date BETWEEN :desde AND :hasta
                    """
                ),
                {
                    "desde": _a_fecha(desde, "desde"),
                    "hasta": _a_fecha(hasta, "hasta"),
                    "tz": settings.zona_horaria_negocio,
                },
            )
        ).scalar_one()
        return float(total or 0)
