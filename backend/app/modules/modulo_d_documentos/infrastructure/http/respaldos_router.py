from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import UsuarioModel
from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_respaldo_repository,
    get_drive_storage,
    get_db,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import (
    RespaldoResponse,
    RespaldosPaginadosResponse,
)
from app.shared.kernel.exceptions import ValidacionError
from app.modules.modulo_d_documentos.application.crear_respaldo_usecase import (
    CrearRespaldoUseCase,
    ObtenerRutaRespaldoUseCase,
)

router = APIRouter(prefix="/respaldos", tags=["Documentos"])


@router.get("", response_model=RespaldosPaginadosResponse)
async def listar_respaldos(
    page: int = 1,
    page_size: int = 20,
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
    db: AsyncSession = Depends(get_db),
):
    """Listado paginado (antes devolvía todos los respaldos generados)."""
    if page < 1:
        raise ValidacionError("page debe ser >= 1.")
    if page_size < 1 or page_size > 100:
        raise ValidacionError("page_size debe estar entre 1 y 100.")
    respaldos, total = await respaldo_repo.listar(page, page_size)

    usuario_ids = {r.usuario_id for r in respaldos if r.usuario_id is not None}
    nombres_map: dict[int, str] = {}
    if usuario_ids:
        resultado = await db.execute(
            select(UsuarioModel.id, UsuarioModel.nombre).where(UsuarioModel.id.in_(usuario_ids))
        )
        nombres_map = {fila.id: fila.nombre for fila in resultado.all()}

    return RespaldosPaginadosResponse(
        items=[
            RespaldoResponse.desde_entidad(r, usuario_nombre=nombres_map.get(r.usuario_id))
            for r in respaldos
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/{respaldo_id}/descargar")
async def descargar_respaldo(
    respaldo_id: int,
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
    drive_storage=Depends(get_drive_storage),
):
    use_case = ObtenerRutaRespaldoUseCase(respaldo_repo, drive_storage)
    contenido, nombre = await use_case.ejecutar(respaldo_id)
    return Response(
        content=contenido,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("", response_model=RespaldoResponse, status_code=201)
async def crear_respaldo(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
    drive_storage=Depends(get_drive_storage),
):
    use_case = CrearRespaldoUseCase(respaldo_repo, drive_storage)
    respaldo = await use_case.ejecutar(usuario_id=usuario.id)
    return RespaldoResponse.desde_entidad(respaldo)

