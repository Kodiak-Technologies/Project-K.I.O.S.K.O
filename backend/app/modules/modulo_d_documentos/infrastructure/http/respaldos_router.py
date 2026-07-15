from fastapi import APIRouter, Depends

from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.infrastructure.dependencies import get_respaldo_repository
from app.modules.modulo_d_documentos.infrastructure.http.schemas import RespaldoResponse

router = APIRouter(prefix="/respaldos", tags=["Documentos"])


@router.get("", response_model=list[RespaldoResponse])
async def listar_respaldos(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    respaldos = await respaldo_repo.listar()
    return [RespaldoResponse.desde_entidad(r) for r in respaldos]


@router.post("", response_model=RespaldoResponse, status_code=201)
async def crear_respaldo(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    from app.modules.modulo_d_documentos.domain.entities import Respaldo
    from datetime import datetime, timezone

    respaldo = Respaldo(
        id=None,
        archivo_nombre=f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.dump",
        estado="PENDIENTE",
    )
    resultado = await respaldo_repo.crear(respaldo)
    return RespaldoResponse.desde_entidad(resultado)
