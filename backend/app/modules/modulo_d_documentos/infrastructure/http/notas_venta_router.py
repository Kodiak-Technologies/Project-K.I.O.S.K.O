import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.application.generar_nota_venta_usecase import GenerarNotaVentaUseCase
from app.modules.modulo_d_documentos.application.descargar_notas_venta_usecase import DescargarNotasVentaUseCase
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_venta_data_provider,
    get_configuracion_provider,
    get_png_generator,
    get_drive_storage,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import (
    NotaVentaResponse,
    NotasVentaPaginadasResponse,
    DescargarNotasRequest,
    SubirNotaDriveResponse,
)
from app.shared.kernel.exceptions import ValidacionError
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort

# Las notas archivadas van junto a las boletas de ingreso, en subcarpetas:
#   boletas/ingresos  (fotos de boleta de las solicitudes)
#   boletas/ventas    (notas de venta subidas a mano, esto)
CARPETA_DRIVE_VENTAS = "boletas/ventas"

router = APIRouter(prefix="/notas-venta", tags=["Documentos"])


@router.get("", response_model=NotasVentaPaginadasResponse)
async def listar_notas_venta(
    desde: str | None = None,
    hasta: str | None = None,
    page: int = 1,
    page_size: int = 20,
    usuario: Usuario = Depends(get_current_user),
    venta_data: VentaDataProviderPort = Depends(get_venta_data_provider),
):
    """Listado paginado (mismo contrato que el resto de las tablas del sistema).

    Antes devolvía TODAS las notas del rango en una sola respuesta y el frontend
    las acumulaba sin límite.
    """
    if page < 1:
        raise ValidacionError("page debe ser >= 1.")
    if page_size < 1 or page_size > 100:
        raise ValidacionError("page_size debe estar entre 1 y 100.")

    # La paginación baja hasta `/ventas`: antes se traía el histórico completo
    # por HTTP y se recortaba en memoria, así que cada request costaba lo mismo
    # que exportar todo el rango.
    pagina, total = await venta_data.listar_ventas_paginado(
        desde=desde, hasta=hasta, page=page, page_size=page_size
    )
    return NotasVentaPaginadasResponse(
        items=[NotaVentaResponse.desde_venta(v) for v in pagina],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


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


@router.post("/{venta_id}/drive", response_model=SubirNotaDriveResponse)
async def subir_nota_a_drive(
    venta_id: int,
    usuario: Usuario = Depends(get_current_user),
    venta_data: VentaDataProviderPort = Depends(get_venta_data_provider),
    config_data=Depends(get_configuracion_provider),
    png_generator=Depends(get_png_generator),
    drive=Depends(get_drive_storage),
):
    """Sube la nota de venta a `boletas/ventas` del Drive del negocio.

    Es a pedido, no automático: se dispara desde el botón de la pantalla de
    Notas de Venta. La nota se sigue generando al vuelo; esto sólo archiva una
    copia.
    """
    png = await GenerarNotaVentaUseCase(venta_data, config_data, png_generator).ejecutar(
        venta_id
    )
    nombre = f"VENTA-{venta_id}.png"
    try:
        file_id = await drive.subir(png, nombre, CARPETA_DRIVE_VENTAS)
    except Exception as exc:  # noqa: BLE001
        # Drive usa OAuth: si se revocó el permiso, hay que decir qué hacer en
        # vez de devolver un 500 opaco.
        raise HTTPException(
            status_code=502,
            detail="No se pudo subir a Google Drive. Verificá que la cuenta "
            "siga autorizada en Configuración → Drive.",
        ) from exc
    return SubirNotaDriveResponse(
        venta_id=venta_id,
        drive_file_id=file_id,
        url=await drive.obtener_url(file_id),
        carpeta=CARPETA_DRIVE_VENTAS,
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
