# Caso de uso: rechazar una merma (CU-B09c, REQ-RECH).
# - SELECT ... FOR UPDATE.
# - Valida motivo >= 5 chars.
# - UPDATE estado='Rechazada' con motivo.
# - NO toca stock, NO crea movimiento.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
    MermaRepositoryPort,
)


class RechazarMermaUseCase:
    def __init__(
        self,
        merma_repo: MermaRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._mermas = merma_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        merma_id: int,
        motivo: str,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Merma:
        from app.shared.kernel.exceptions import (
            ConflictoError,
            NoEncontradoError,
            ValidacionError,
        )

        motivo_limpio = (motivo or "").strip()
        if len(motivo_limpio) < 5:
            raise ValidacionError(
                "El motivo de rechazo debe tener al menos 5 caracteres."
            )
        merma = await self._mermas.find_by_id_for_update(merma_id)
        if merma is None:
            raise NoEncontradoError("La merma no existe.")
        # EC-17 / FR-5.4: differentiate "already rejected" from "already confirmed"
        # so the frontend can show a precise error message.
        from app.modules.modulo_b_inventario.domain.value_objects import EstadoMerma
        if str(merma.estado) == str(EstadoMerma("Rechazada")):
            raise ConflictoError(
                "La merma ya fue rechazada.", code="ALREADY_REJECTED"
            )
        if not merma.puede_ser_rechazada():
            raise ConflictoError(
                "La merma ya fue confirmada o rechazada.", code="ALREADY_REJECTED"
            )
        merma.rechazar(usuario_id, usuario_nombre, motivo_limpio)
        await self._mermas.actualizar(merma)
        await self._auditoria.ejecutar(
            accion="rechazar_merma",
            entidad="mermas",
            usuario_id=usuario_id,
            rol="",
            entidad_id=merma_id,
            motivo=motivo_limpio,
            ip=ip,
            user_agent=user_agent,
        )
        return merma
