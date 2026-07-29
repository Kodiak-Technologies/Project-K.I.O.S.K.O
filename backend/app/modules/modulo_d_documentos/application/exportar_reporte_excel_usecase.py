from app.modules.modulo_d_documentos.domain.ports.reporte_generator_port import ReporteGeneratorPort
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort
from app.modules.modulo_d_documentos.domain.ports.configuracion_provider_port import ConfiguracionProviderPort
from app.modules.modulo_d_documentos.domain.ports.egresos_data_provider_port import EgresosDataProviderPort
from app.modules.modulo_d_documentos.domain.ports.metodo_pago_provider_port import MetodoPagoProviderPort
from app.modules.modulo_d_documentos.application.generar_reporte_ventas_usecase import GenerarReporteVentasUseCase
from app.modules.modulo_d_documentos.application.generar_reporte_mas_vendidos_usecase import GenerarReporteMasVendidosUseCase


class ExportarReporteExcelUseCase:
    def __init__(
        self,
        reporte_generator: ReporteGeneratorPort,
        venta_data: VentaDataProviderPort,
        config_data: ConfiguracionProviderPort,
        egresos_data: EgresosDataProviderPort,
        metodo_pago_data: MetodoPagoProviderPort | None = None,
    ) -> None:
        self._reporte_generator = reporte_generator
        self._venta_data = venta_data
        self._config_data = config_data
        self._egresos_data = egresos_data
        self._metodo_pago_data = metodo_pago_data

    async def ejecutar(
        self,
        desde: str,
        hasta: str,
        tipo: str = "resumen",
    ) -> bytes:
        config = await self._config_data.obtener()
        nombre_negocio = config.get("nombre_negocio", "Mi Tienda")

        if tipo == "mas_vendidos":
            use_case = GenerarReporteMasVendidosUseCase(self._venta_data)
            datos = {
                "titulo": f"Productos Más Vendidos — {nombre_negocio}",
                "periodo": f"{desde} al {hasta}",
                "productos": [
                    {"nombre": p.nombre, "cantidad": p.cantidad, "total": p.total}
                    for p in await use_case.ejecutar(desde, hasta)
                ],
            }
        elif tipo == "egresos":
            egresos = await self._egresos_data.obtener_egresos(desde, hasta)
            total_egresos = sum(e.get("monto", 0) for e in egresos)
            datos = {
                "titulo": f"Reporte de Egresos — {nombre_negocio}",
                "periodo": f"{desde} al {hasta}",
                "total_egresos": total_egresos,
                "numero_registros": len(egresos),
                "egresos": egresos,
                "costo_por_proveedor": await self._egresos_data.costo_por_proveedor(
                    desde, hasta
                ),
            }
        else:
            use_case = GenerarReporteVentasUseCase(
                self._venta_data, self._egresos_data, self._metodo_pago_data
            )
            resumen = await use_case.ejecutar(desde, hasta)
            datos = {
                "titulo": f"Reporte de Ventas — {nombre_negocio}",
                "periodo": f"{desde} al {hasta}",
                "total_vendido": resumen.total_vendido,
                "total_egresos": resumen.total_egresos,
                "total_devuelto": resumen.total_devuelto,
                "utilidad_neta": resumen.total_vendido - resumen.total_egresos,
                "numero_ventas": resumen.numero_ventas,
                "ticket_promedio": resumen.ticket_promedio,
                "metodos_pago": resumen.metodos_pago,
                "top_productos": [
                    {"nombre": p.nombre, "cantidad": p.cantidad, "total": p.total}
                    for p in resumen.top_productos
                ],
                "costo_por_proveedor": [
                    {
                        "proveedor": c.proveedor,
                        "monto": c.monto,
                        "unidades": c.unidades,
                        "ingresos": c.ingresos,
                    }
                    for c in resumen.costo_por_proveedor
                ],
            }

        nombre_archivo = f"reporte_{tipo}_{desde}_{hasta}"
        return await self._reporte_generator.generar_excel(datos, nombre_archivo)
