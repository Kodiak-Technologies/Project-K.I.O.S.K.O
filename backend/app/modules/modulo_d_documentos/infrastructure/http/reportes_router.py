from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user, require_permission
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.application.generar_reporte_ventas_usecase import GenerarReporteVentasUseCase
from app.modules.modulo_d_documentos.application.exportar_reporte_excel_usecase import ExportarReporteExcelUseCase
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_venta_data_provider,
    get_configuracion_provider,
    get_reporte_generator,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import ReporteResumenResponse
import io

router = APIRouter(prefix="/reportes", tags=["Documentos"])


@router.get("/resumen", response_model=ReporteResumenResponse)
async def obtener_resumen(
    desde: str,
    hasta: str,
    usuario: Usuario = Depends(require_permission("reportes.ver")),
    venta_data=Depends(get_venta_data_provider),
):
    use_case = GenerarReporteVentasUseCase(venta_data)
    resumen = await use_case.ejecutar(desde, hasta)
    return ReporteResumenResponse.desde_entidad(resumen)


@router.get("/exportar")
async def exportar_reporte(
    desde: str,
    hasta: str,
    tipo: str = "resumen",
    usuario: Usuario = Depends(require_permission("reportes.ver")),
    venta_data=Depends(get_venta_data_provider),
    config_data=Depends(get_configuracion_provider),
    reporte_generator=Depends(get_reporte_generator),
):
    use_case = ExportarReporteExcelUseCase(reporte_generator, venta_data, config_data)
    excel_bytes = await use_case.ejecutar(desde, hasta, tipo)

    filename = f"reporte_{tipo}_{desde}_{hasta}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
