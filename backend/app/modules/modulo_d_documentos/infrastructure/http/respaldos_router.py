from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.infrastructure.dependencies import get_respaldo_repository
from app.modules.modulo_d_documentos.infrastructure.http.schemas import RespaldoResponse
from app.modules.modulo_d_documentos.application.crear_respaldo_usecase import (
    CrearRespaldoUseCase,
    ObtenerRutaRespaldoUseCase,
)

router = APIRouter(prefix="/respaldos", tags=["Documentos"])


@router.get("", response_model=list[RespaldoResponse])
async def listar_respaldos(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    respaldos = await respaldo_repo.listar()
    return [RespaldoResponse.desde_entidad(r) for r in respaldos]


@router.get("/{respaldo_id}/descargar")
async def descargar_respaldo(
    respaldo_id: int,
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    use_case = ObtenerRutaRespaldoUseCase(respaldo_repo)
    ruta, nombre = await use_case.ejecutar(respaldo_id)
    return FileResponse(
        path=ruta,
        media_type="application/octet-stream",
        filename=nombre,
    )


@router.post("", response_model=RespaldoResponse, status_code=201)
async def crear_respaldo(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    use_case = CrearRespaldoUseCase(respaldo_repo)
    respaldo = await use_case.ejecutar()
    return RespaldoResponse.desde_entidad(respaldo)
