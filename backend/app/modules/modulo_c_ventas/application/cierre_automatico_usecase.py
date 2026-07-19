import logging
from datetime import datetime

from app.modules.modulo_c_ventas.domain.entities import ArqueoCaja
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.application.cerrar_caja_usecase import calcular_resumen

logger = logging.getLogger(__name__)

COMENTARIO_AUTOMATICO = "Cierre automático: turno no cerrado al finalizar la jornada."
CERRADO_POR_SISTEMA = "Sistema"


class CierreAutomaticoUseCase:
    def __init__(self, caja_repo: CajaRepositoryPort):
        self._caja = caja_repo

    async def ejecutar(self) -> None:
        try:
            turno = await self._caja.turno_abierto()
            if turno is None:
                return

            ahora_local = datetime.now()
            apertura_local = (
                turno.abierto_en.astimezone().replace(tzinfo=None)
                if turno.abierto_en.tzinfo
                else turno.abierto_en
            )

            if apertura_local.date() >= ahora_local.date():
                return

            resumen = await calcular_resumen(self._caja, turno)

            turno_cerrado = await self._caja.cerrar(
                turno_id=turno.id,
                monto_final=resumen.efectivo_esperado,
                usuario_cierre_id=None,
                cerrado_por=CERRADO_POR_SISTEMA,
            )

            await self._caja.guardar_arqueo(
                ArqueoCaja(
                    id=None,
                    turno_id=turno.id,
                    usuario_id=None,
                    cerrado_por=CERRADO_POR_SISTEMA,
                    efectivo_esperado=resumen.efectivo_esperado,
                    efectivo_contado=resumen.efectivo_esperado,
                    diferencia=resumen.efectivo_esperado - resumen.efectivo_esperado,
                    comentario=COMENTARIO_AUTOMATICO,
                    total_vendido=resumen.total_vendido,
                    totales_por_metodo=resumen.totales_por_metodo,
                )
            )

            logger.warning(
                "Cierre automático del turno #%s (apertura: %s). Efectivo calculado: S/ %s.",
                turno_cerrado.id,
                apertura_local.strftime("%Y-%m-%d %H:%M"),
                resumen.efectivo_esperado,
            )

        except Exception as exc:
            logger.error("Error en cierre automático de caja: %s", exc, exc_info=True)
