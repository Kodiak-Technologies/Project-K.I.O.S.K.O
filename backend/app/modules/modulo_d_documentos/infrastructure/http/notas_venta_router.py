import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user, require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.application.generar_nota_venta_usecase import GenerarNotaVentaUseCase
from app.modules.modulo_d_documentos.application.descargar_notas_venta_usecase import DescargarNotasVentaUseCase
from app.modules.modulo_d_documentos.application.subir_notas_drive_usecase import SubirNotasDriveUseCase
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_venta_data_provider,
    get_configuracion_provider,
    get_png_generator,
    get_drive_storage,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import (
    NotaVentaResponse,
    DescargarNotasRequest,
    SubirNotasDriveRequest,
)
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort

router = APIRouter(prefix="/notas-venta", tags=["Documentos"])


@router.get("", response_model=list[NotaVentaResponse])
async def listar_notas_venta(
    desde: str | None = None,
    hasta: str | None = None,
    usuario: Usuario = Depends(get_current_user),
    venta_data: VentaDataProviderPort = Depends(get_venta_data_provider),
):
    ventas = await venta_data.listar_ventas(desde=desde, hasta=hasta)
    return [NotaVentaResponse.desde_venta(v) for v in ventas]


@router.get("/{venta_id}/png")
async def descargar_nota_venta_png(
    venta_id: int,
    usuario: Usuario = Depends(get_current_user),
    venta_data: VentaDataProviderPort = Depends(get_venta_data_provider),
    config_data=Depends(get_configuracion_provider),
    png_generator=Depends(get_png_generator),
):
    usecase = GenerarNotaVentaUseCase(venta_data, config_data, png_generator)
    png_bytes = await usecase.ejecutar(venta_id)

    filename = f"NOTA-VENTA-{venta_id}.png"
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/descargar")
async def descargar_notas_venta_batch(
    body: DescargarNotasRequest,
    usuario: Usuario = Depends(get_current_user),
    venta_data: VentaDataProviderPort = Depends(get_venta_data_provider),
    config_data=Depends(get_configuracion_provider),
    png_generator=Depends(get_png_generator),
):
    generar_nota = GenerarNotaVentaUseCase(venta_data, config_data, png_generator)
    usecase = DescargarNotasVentaUseCase(venta_data, generar_nota)
    data, count = await usecase.ejecutar(desde=body.desde, hasta=body.hasta)

    if count == 0:
        raise HTTPException(status_code=404, detail="No se encontraron ventas en el rango dado")

    if count == 1:
        return StreamingResponse(
            io.BytesIO(data),
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=nota-venta.png"},
        )

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=notas-venta.zip"},
    )


@router.post("/subir-drive")
async def subir_notas_drive_batch(
    body: SubirNotasDriveRequest,
    usuario: Usuario = Depends(require_role("ADMIN")),
    venta_data: VentaDataProviderPort = Depends(get_venta_data_provider),
    config_data=Depends(get_configuracion_provider),
    png_generator=Depends(get_png_generator),
    drive_storage=Depends(get_drive_storage),
):
    generar_nota = GenerarNotaVentaUseCase(venta_data, config_data, png_generator)
    usecase = SubirNotasDriveUseCase(venta_data, generar_nota, drive_storage)
    resultado = await usecase.ejecutar(desde=body.desde, hasta=body.hasta, carpeta=body.carpeta)
    return resultado
