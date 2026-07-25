# Caso de uso: rechazar una solicitud de ingreso (HU-B07, REQ-RECH).
# - Valida motivo >= 5 chars.
# - SELECT ... FOR UPDATE + UPDATE estado.
# - NO toca stock, NO crea movimiento.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import SolicitudIngreso
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)


class RechazarIngresoUseCase:
    def __init__(
        self,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._solicitudes = solicitud_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        solicitud_id: int,
        motivo: str,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> SolicitudIngreso:
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
        solicitud = await self._solicitudes.find_by_id_for_update(solicitud_id)
        if solicitud is None:
            raise NoEncontradoError("La solicitud no existe.")
        # FR-5.4 (symmetric to mermas): differentiate "already rejected" vs
        # "already approved" so the frontend can show a precise error code.
        from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud
        if str(solicitud.estado) == str(EstadoSolicitud("Rechazada")):
            raise ConflictoError(
                "La solicitud ya fue rechazada.", code="ALREADY_REJECTED"
            )
        if not solicitud.puede_ser_rechazada():
            raise ConflictoError(
                "La solicitud ya fue aprobada o rechazada.", code="ALREADY_REJECTED"
            )
        solicitud.rechazar(usuario_id, usuario_nombre, motivo_limpio)
        await self._solicitudes.actualizar(solicitud)
        await self._auditoria.ejecutar(
            accion="rechazar_ingreso",
            entidad="solicitudes_ingreso",
            usuario_id=usuario_id,
            rol="",
            entidad_id=solicitud_id,
            motivo=motivo_limpio,
            ip=ip,
            user_agent=user_agent,
        )
        return solicitud
