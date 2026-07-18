import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user, require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.application.generar_boleta_usecase import GenerarBoletaUseCase
from app.modules.modulo_d_documentos.application.subir_boleta_drive_usecase import SubirBoletaDriveUseCase
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_boleta_repository,
    get_venta_data_provider,
    get_configuracion_provider,
    get_drive_storage,
    get_archivo_drive_repository,
    get_png_generator,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import BoletaResponse, ArchivoDriveResponse
from app.shared.database.session import get_db
from app.shared.kernel.exceptions import NoEncontradoError

router = APIRouter(prefix="/boletas", tags=["Documentos"])


@router.get("", response_model=list[BoletaResponse])
async def listar_boletas(
    desde: str | None = None,
    hasta: str | None = None,
    q: str | None = None,
    cliente: str | None = None,
    usuario: Usuario = Depends(get_current_user),
    boleta_repo=Depends(get_boleta_repository),
):
    boletas = await boleta_repo.listar(desde=desde, hasta=hasta, q=q, cliente=cliente)
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


@router.post("", response_model=BoletaResponse, status_code=201)
async def crear_boleta(
    venta_id: int,
    usuario: Usuario = Depends(require_role("ADMIN")),
    boleta_repo=Depends(get_boleta_repository),
    venta_data_provider=Depends(get_venta_data_provider),
    configuracion_provider=Depends(get_configuracion_provider),
):
    usecase = GenerarBoletaUseCase(boleta_repo, venta_data_provider, configuracion_provider)
    boleta = await usecase.ejecutar(venta_id)
    return BoletaResponse.desde_entidad(boleta)


@router.post("/{boleta_id}/subir-drive", response_model=ArchivoDriveResponse)
async def subir_boleta_drive(
    boleta_id: int,
    usuario: Usuario = Depends(require_role("ADMIN")),
    boleta_repo=Depends(get_boleta_repository),
    drive_storage=Depends(get_drive_storage),
    archivo_drive_repo=Depends(get_archivo_drive_repository),
    png_generator=Depends(get_png_generator),
    configuracion_provider=Depends(get_configuracion_provider),
):
    usecase = SubirBoletaDriveUseCase(
        boleta_repo=boleta_repo,
        drive_storage=drive_storage,
        archivo_drive_repo=archivo_drive_repo,
        png_generator=png_generator,
        configuracion_provider=configuracion_provider,
    )
    archivo = await usecase.ejecutar(boleta_id)
    return ArchivoDriveResponse.desde_entidad(archivo)


@router.get("/{boleta_id}/png")
async def descargar_png(
    boleta_id: int,
    usuario: Usuario = Depends(get_current_user),
    boleta_repo=Depends(get_boleta_repository),
    png_generator=Depends(get_png_generator),
    configuracion_provider=Depends(get_configuracion_provider),
):
    boleta = await boleta_repo.buscar_por_id(boleta_id)
    if boleta is None:
        raise NoEncontradoError(f"Boleta #{boleta_id} no encontrada")

    nombre_negocio = "Mi Tienda"
    if configuracion_provider:
        config = await configuracion_provider.obtener()
        nombre_negocio = config.get("nombre_negocio", "Mi Tienda")

    fecha = boleta.emitida_en.strftime("%Y-%m-%d %H:%M") if boleta.emitida_en else ""

    png_bytes = await png_generator.generar(
        numero=boleta.numero,
        total=boleta.total,
        fecha=fecha,
        productos=[],
        nombre_negocio=nombre_negocio,
    )

    filename = f"BOL-{boleta.numero}.png"
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
