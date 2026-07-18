from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.modules.modulo_a_seguridad.infrastructure.dependencies import get_current_user, require_permission
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.application.generar_reporte_ventas_usecase import GenerarReporteVentasUseCase
from app.modules.modulo_d_documentos.application.generar_reporte_mas_vendidos_usecase import GenerarReporteMasVendidosUseCase
from app.modules.modulo_d_documentos.application.exportar_reporte_excel_usecase import ExportarReporteExcelUseCase
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    get_venta_data_provider,
    get_configuracion_provider,
    get_reporte_generator,
    get_egresos_data_provider,
    get_metodo_pago_provider,
)
from app.modules.modulo_d_documentos.infrastructure.http.schemas import ReporteResumenResponse, TopProductoResponse
import io

router = APIRouter(prefix="/reportes", tags=["Documentos"])


@router.get("/resumen", response_model=ReporteResumenResponse)
async def obtener_resumen(
    desde: str,
    hasta: str,
    usuario: Usuario = Depends(require_permission("reportes.ver")),
    venta_data=Depends(get_venta_data_provider),
    egresos_data=Depends(get_egresos_data_provider),
    metodo_pago_data=Depends(get_metodo_pago_provider),
):
    use_case = GenerarReporteVentasUseCase(venta_data, egresos_data, metodo_pago_data)
    resumen = await use_case.ejecutar(desde, hasta)
    return ReporteResumenResponse.desde_entidad(resumen)


@router.get("/mas-vendidos", response_model=list[TopProductoResponse])
async def obtener_mas_vendidos(
    desde: str,
    hasta: str,
    criterio: str = "unidades",
    orden: str = "mayor",
    usuario: Usuario = Depends(require_permission("reportes.ver")),
    venta_data=Depends(get_venta_data_provider),
):
    use_case = GenerarReporteMasVendidosUseCase(venta_data)
    productos = await use_case.ejecutar(desde, hasta, criterio=criterio, orden=orden)
    return [TopProductoResponse.desde_entidad(p) for p in productos]


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
