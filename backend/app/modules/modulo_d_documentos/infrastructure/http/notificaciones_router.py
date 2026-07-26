from fastapi import APIRouter, Depends

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user, require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.application.enviar_notificacion_usecase import EnviarNotificacionUseCase
from app.modules.modulo_d_documentos.application.marcar_notificacion_leida_usecase import MarcarNotificacionLeidaUseCase
from app.modules.modulo_d_documentos.application.marcar_todas_notificaciones_leidas_usecase import MarcarTodasNotificacionesLeidasUseCase
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_notificacion_repository,
    get_config_notificaciones_repository,
    get_notificacion_sender,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import (
    NotificacionResponse,
    NotificacionesPaginadasResponse,
    MarcarLeidaRequest,
    ConfigNotificacionesResponse,
    ConfigNotificacionesRequest,
    CrearNotificacionRequest,
)
from app.modules.modulo_d_documentos.domain.entities import Notificacion, ConfigNotificaciones
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError

router = APIRouter(prefix="/notificaciones", tags=["Documentos"])


@router.get("", response_model=NotificacionesPaginadasResponse)
async def listar_notificaciones(
    page: int = 1,
    page_size: int = 20,
    usuario: Usuario = Depends(get_current_user),
    notificacion_repo=Depends(get_notificacion_repository),
):
    """Bandeja paginada (antes devolvía todas las notificaciones del usuario)."""
    if page < 1:
        raise ValidacionError("page debe ser >= 1.")
    if page_size < 1 or page_size > 100:
        raise ValidacionError("page_size debe estar entre 1 y 100.")
    notificaciones, total = await notificacion_repo.listar_por_usuario(
        usuario.id, page, page_size
    )
    return NotificacionesPaginadasResponse(
        items=[NotificacionResponse.desde_entidad(n) for n in notificaciones],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.post("/{notificacion_id}/leida", status_code=200)
async def marcar_leida(
    notificacion_id: int,
    usuario: Usuario = Depends(get_current_user),
    notificacion_repo=Depends(get_notificacion_repository),
):
    usecase = MarcarNotificacionLeidaUseCase(notificacion_repo)
    resultado = await usecase.ejecutar(notificacion_id)
    if resultado is None:
        raise NoEncontradoError(f"Notificación #{notificacion_id} no encontrada")
    return NotificacionResponse.desde_entidad(resultado)


@router.post("/leer-todas", status_code=200)
async def marcar_todas_leidas(
    usuario: Usuario = Depends(get_current_user),
    notificacion_repo=Depends(get_notificacion_repository),
):
    usecase = MarcarTodasNotificacionesLeidasUseCase(notificacion_repo)
    cantidad = await usecase.ejecutar(usuario.id)
    return {"marcadas": cantidad}


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
    existente = await config_repo.obtener()
    config = ConfigNotificaciones(
        id=1,
        nivel_detalle=body.nivel_detalle if body.nivel_detalle is not None else existente.nivel_detalle,
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
    use_case = EnviarNotificacionUseCase(notificacion_sender, notificacion_repo, config_repo)
    notificacion = await use_case.ejecutar(
        tipo=body.tipo,
        titulo=body.titulo,
        mensaje=body.mensaje,
        entidad_origen=body.entidad_origen,
        entidad_id=body.entidad_id,
        usuario_id=body.usuario_id,
        producto_id=body.producto_id,
    )
    return NotificacionResponse.desde_entidad(notificacion)
