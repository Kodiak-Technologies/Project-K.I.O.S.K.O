# Caso de uso: cerrar caja al final de un turno y cuadrar el efectivo (RF-17).
#
# El cierre es "automático como sugerencia": el sistema calcula el efectivo
# esperado (inicial + ventas en efectivo + abonos - devoluciones) y el cajero
# solo confirma o corrige con lo que contó físicamente. Lo vendido por Yape,
# tarjeta, etc. se muestra aparte: ese dinero existe pero NO está en el cajón.
# Si el monto contado difiere de la sugerencia, el comentario es OBLIGATORIO y
# el descuadre queda registrado para que la administradora lo revise.
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import ArqueoCaja, ResumenCaja, TurnoCaja
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import monto_dinero
from app.shared.kernel.exceptions import ConflictoError, ValidacionError


async def calcular_resumen(caja_repo: CajaRepositoryPort, turno: TurnoCaja) -> ResumenCaja:
    """Foto del turno para la pantalla de cierre y para el arqueo definitivo."""
    totales = await caja_repo.totales_de_turno(turno.id)
    esperado = monto_dinero(
        turno.monto_inicial
        + totales["ventas_efectivo"]
        + totales["abonos_efectivo"]
        - totales["devoluciones_efectivo"]
    )
    return ResumenCaja(
        turno=turno,
        efectivo_esperado=esperado,
        monto_inicial=turno.monto_inicial,
        ventas_efectivo=monto_dinero(totales["ventas_efectivo"]),
        abonos_efectivo=monto_dinero(totales["abonos_efectivo"]),
        devoluciones_efectivo=monto_dinero(totales["devoluciones_efectivo"]),
        totales_por_metodo=totales["totales_por_metodo"],
        total_vendido=monto_dinero(totales["total_vendido"]),
        numero_ventas=totales["numero_ventas"],
    )


class CerrarCajaUseCase:
    def __init__(self, caja_repo: CajaRepositoryPort, auditoria: RegistrarAuditoriaUseCase):
        self._caja = caja_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        usuario_id: int,
        nombre_usuario: str,
        rol: str,
        monto_final: Decimal,
        comentario: str | None = None,
        ip: str = "",
        user_agent: str = "",
    ) -> tuple[TurnoCaja, ArqueoCaja]:
        turno = await self._caja.turno_abierto()
        if turno is None:
            raise ConflictoError("No hay un turno de caja abierto que cerrar.")

        contado = monto_dinero(monto_final)
        resumen = await calcular_resumen(self._caja, turno)
        diferencia = monto_dinero(contado - resumen.efectivo_esperado, minimo=None)

        comentario = (comentario or "").strip() or None
        if diferencia != 0 and comentario is None:
            signo = "faltan" if diferencia < 0 else "sobran"
            raise ValidacionError(
                f"El monto contado difiere de la sugerencia del sistema "
                f"(S/ {resumen.efectivo_esperado}): {signo} S/ {abs(diferencia)}. "
                "Explica el motivo en el comentario para poder cerrar."
            )

        turno_cerrado = await self._caja.cerrar(turno.id, contado, usuario_id, nombre_usuario)
        arqueo = await self._caja.guardar_arqueo(
            ArqueoCaja(
                id=None,
                turno_id=turno.id,
                usuario_id=usuario_id,
                cerrado_por=nombre_usuario,
                efectivo_esperado=resumen.efectivo_esperado,
                efectivo_contado=contado,
                diferencia=diferencia,
                comentario=comentario,
                total_vendido=resumen.total_vendido,
                totales_por_metodo=resumen.totales_por_metodo,
            )
        )

        await self._auditoria.ejecutar(
            accion="caja_cerrada", entidad="turnos_caja", entidad_id=turno.id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={
                "efectivo_esperado": float(resumen.efectivo_esperado),
                "efectivo_contado": float(contado),
                "diferencia": float(diferencia),
                "total_vendido": float(resumen.total_vendido),
            },
            motivo=comentario,
            ip=ip, user_agent=user_agent,
        )
        if diferencia != 0:
            # Evento propio para que la administradora filtre descuadres en la bitácora.
            await self._auditoria.ejecutar(
                accion="caja_descuadre", entidad="turnos_caja", entidad_id=turno.id,
                usuario_id=usuario_id, rol=rol,
                valor_nuevo={"diferencia": float(diferencia)},
                motivo=comentario,
                ip=ip, user_agent=user_agent,
            )
        return turno_cerrado, arqueo
