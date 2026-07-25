from fastapi import APIRouter, Depends, HTTPException
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
from app.modules.modulo_d_documentos.infrastructure.http.schemas import RespaldoResponse
from app.modules.modulo_d_documentos.application.crear_respaldo_usecase import (
    CrearRespaldoUseCase,
    ObtenerRutaRespaldoUseCase,
    RestaurarRespaldoUseCase,
)

router = APIRouter(prefix="/respaldos", tags=["Documentos"])


@router.get("", response_model=list[RespaldoResponse])
async def listar_respaldos(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
    db: AsyncSession = Depends(get_db),
):
    respaldos = await respaldo_repo.listar()

    usuario_ids = {r.usuario_id for r in respaldos if r.usuario_id is not None}
    nombres_map: dict[int, str] = {}
    if usuario_ids:
        resultado = await db.execute(
            select(UsuarioModel.id, UsuarioModel.nombre).where(UsuarioModel.id.in_(usuario_ids))
        )
        nombres_map = {fila.id: fila.nombre for fila in resultado.all()}

    return [
        RespaldoResponse.desde_entidad(r, usuario_nombre=nombres_map.get(r.usuario_id))
        for r in respaldos
    ]


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


@router.post("/{respaldo_id}/restaurar", status_code=200)
async def restaurar_respaldo(
    respaldo_id: int,
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
    drive_storage=Depends(get_drive_storage),
):
    use_case = RestaurarRespaldoUseCase(respaldo_repo, drive_storage)
    ok = await use_case.ejecutar(respaldo_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Error al restaurar respaldo")
    return {"detail": "Respaldo restaurado correctamente"}
