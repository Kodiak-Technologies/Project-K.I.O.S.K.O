# Caso de uso: abrir caja al inicio de un turno.
# La apertura es MANUAL: el cajero cuenta el efectivo (sencillo para el vuelto)
# y lo registra. Sin turno abierto no se puede vender (validado en RegistrarVenta).
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import TurnoCaja
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import monto_dinero
from app.shared.kernel.exceptions import ConflictoError


class AbrirCajaUseCase:
    def __init__(self, caja_repo: CajaRepositoryPort, auditoria: RegistrarAuditoriaUseCase):
        self._caja = caja_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        usuario_id: int,
        nombre_usuario: str,
        rol: str,
        monto_inicial: Decimal,
        ip: str = "",
        user_agent: str = "",
    ) -> TurnoCaja:
        monto = monto_dinero(monto_inicial)

        abierto = await self._caja.turno_abierto()
        if abierto is not None:
            raise ConflictoError(
                f"La caja ya está abierta por {abierto.abierto_por}. "
                "Cierra ese turno antes de abrir uno nuevo."
            )

        turno = await self._caja.abrir(
            TurnoCaja(
                id=None,
                usuario_id=usuario_id,
                abierto_por=nombre_usuario,
                monto_inicial=monto,
            )
        )
        await self._auditoria.ejecutar(
            accion="caja_abierta", entidad="turnos_caja", entidad_id=turno.id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={"monto_inicial": float(monto)},
            ip=ip, user_agent=user_agent,
        )
        return turno
