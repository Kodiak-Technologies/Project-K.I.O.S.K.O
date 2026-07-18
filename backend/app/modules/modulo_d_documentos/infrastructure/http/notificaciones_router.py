from fastapi import APIRouter, Depends

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user, require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_notificacion_repository,
    get_config_notificaciones_repository,
    get_notificacion_sender,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import (
    NotificacionResponse,
    MarcarLeidaRequest,
    ConfigNotificacionesResponse,
    ConfigNotificacionesRequest,
    CrearNotificacionRequest,
)
from app.modules.modulo_d_documentos.domain.entities import Notificacion, ConfigNotificaciones
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


@router.get("/config", response_model=ConfigNotificacionesResponse)
async def obtener_config(
    usuario: Usuario = Depends(get_current_user),
    config_repo=Depends(get_config_notificaciones_repository),
):
    config = await config_repo.obtener()
    return ConfigNotificacionesResponse.desde_entidad(config)


@router.put("/config", response_model=ConfigNotificacionesResponse)
async def actualizar_config(
    body: ConfigNotificacionesRequest,
    usuario: Usuario = Depends(require_role("ADMIN")),
    config_repo=Depends(get_config_notificaciones_repository),
):
    config = ConfigNotificaciones(
        id=1,
        canal_telegram_activo=body.canal_telegram_activo,
        canal_correo_activo=body.canal_correo_activo,
        nivel_detalle=body.nivel_detalle,
        telegram_chat_id=body.telegram_chat_id,
        correo_destino=body.correo_destino,
    )
    resultado = await config_repo.actualizar(config)
    return ConfigNotificacionesResponse.desde_entidad(resultado)


@router.post("", response_model=NotificacionResponse, status_code=201)
async def crear_notificacion(
    body: CrearNotificacionRequest,
    usuario: Usuario = Depends(require_role("ADMIN")),
    notificacion_repo=Depends(get_notificacion_repository),
    config_repo=Depends(get_config_notificaciones_repository),
    notificacion_sender=Depends(get_notificacion_sender),
):
    config = await config_repo.obtener()

    notificacion = Notificacion(
        id=None,
        tipo=body.tipo,
        titulo=body.titulo,
        mensaje=body.mensaje,
        entidad_origen=body.entidad_origen,
        entidad_id=body.entidad_id,
        usuario_id=body.usuario_id,
    )
    notificacion = await notificacion_repo.crear(notificacion)

    if config.canal_telegram_activo and notificacion_sender:
        await notificacion_sender.enviar("TELEGRAM", body.titulo, body.mensaje)

    return NotificacionResponse.desde_entidad(notificacion)
