# Adaptador: desglose real de la recaudación por método de pago.
#
# Sale de `pagos_venta` (un renglón por método usado en cada venta, con snapshot
# del código), no del resumen `ventas.metodo_pago` —que dice "MIXTO" cuando la
# venta se pagó con más de uno y perdería el detalle—.
#
# Las ventas anuladas quedan fuera: no son plata recaudada. El día se calcula en
# la zona del negocio, igual que los egresos.
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


class SqlMetodoPagoProvider:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def desglose_por_metodo(self, desde: str, hasta: str) -> dict[str, float]:
        filas = (
            await self._db.execute(
                text(
                    """
                    SELECT pv.codigo_metodo AS metodo,
                           SUM(pv.monto)    AS total
                    FROM pagos_venta pv
                    JOIN ventas v ON v.id = pv.venta_id
                    WHERE v.estado <> 'ANULADA'
                      AND (COALESCE(v.vendida_en, v.created_at) AT TIME ZONE :tz)::date
                          BETWEEN :desde AND :hasta
                    GROUP BY pv.codigo_metodo
                    ORDER BY SUM(pv.monto) DESC
                    """
                ),
                {
                    "desde": _a_fecha(desde, "desde"),
                    "hasta": _a_fecha(hasta, "hasta"),
                    "tz": settings.zona_horaria_negocio,
                },
            )
        ).all()
        return {fila.metodo: float(fila.total or 0) for fila in filas}
