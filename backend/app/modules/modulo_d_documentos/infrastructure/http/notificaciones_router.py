from fastapi import APIRouter, Depends

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.infrastructure.dependencies import get_notificacion_repository
from app.modules.modulo_d_documentos.infrastructure.http.schemas import NotificacionResponse, MarcarLeidaRequest
from app.shared.kernel.exceptions import NoEncontradoError

router = APIRouter(prefix="/notificaciones", tags=["Documentos"])


@router.get("", response_model=list[NotificacionResponse])
async def listar_notificaciones(
    usuario: Usuario = Depends(get_current_user),
    notificacion_repo=Depends(get_notificacion_repository),
):
    notificaciones = await notificacion_repo.listar()
    return [NotificacionResponse.desde_entidad(n) for n in notificaciones]


@router.post("/{notificacion_id}/leida", status_code=200)
async def marcar_leida(
    notificacion_id: int,
    usuario: Usuario = Depends(get_current_user),
    notificacion_repo=Depends(get_notificacion_repository),
):
    resultado = await notificacion_repo.marcar_leida(notificacion_id)
    if resultado is None:
        raise NoEncontradoError(f"Notificación #{notificacion_id} no encontrada")
    return NotificacionResponse.desde_entidad(resultado)
