from fastapi import APIRouter, Depends

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.application.generar_boleta_usecase import GenerarBoletaUseCase
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_boleta_repository,
    get_venta_data_provider,
    get_configuracion_provider,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import BoletaResponse
from app.shared.database.session import get_db

router = APIRouter(prefix="/boletas", tags=["Documentos"])


@router.get("", response_model=list[BoletaResponse])
async def listar_boletas(
    desde: str | None = None,
    hasta: str | None = None,
    q: str | None = None,
    usuario: Usuario = Depends(get_current_user),
    boleta_repo=Depends(get_boleta_repository),
):
    boletas = await boleta_repo.listar(desde=desde, hasta=hasta, q=q)
    return [BoletaResponse.desde_entidad(b) for b in boletas]


@router.get("/{boleta_id}", response_model=BoletaResponse)
async def obtener_boleta(
    boleta_id: int,
    usuario: Usuario = Depends(get_current_user),
    boleta_repo=Depends(get_boleta_repository),
):
    boleta = await boleta_repo.buscar_por_id(boleta_id)
    if boleta is None:
        from app.shared.kernel.exceptions import NoEncontradoError
        raise NoEncontradoError(f"Boleta #{boleta_id} no encontrada")
    return BoletaResponse.desde_entidad(boleta)
