from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort
from app.modules.modulo_d_documentos.domain.ports.configuracion_provider_port import ConfiguracionProviderPort
from app.shared.kernel.exceptions import NoEncontradoError


class GenerarNotaVentaUseCase:
    def __init__(
        self,
        venta_data: VentaDataProviderPort,
        config_data: ConfiguracionProviderPort,
        png_generator,
    ) -> None:
        self._venta_data = venta_data
        self._config_data = config_data
        self._png_generator = png_generator

    async def ejecutar(self, venta_id: int) -> bytes:
        venta = await self._venta_data.obtener_venta(venta_id)
        if venta is None:
            raise NoEncontradoError(f"La venta #{venta_id} no existe.")

        items = await self._venta_data.obtener_detalle_venta(venta_id)
        config = await self._config_data.obtener()

        productos = [
            {
                "nombre": item.get("nombre", item.get("producto_nombre", "")),
                "cantidad": item.get("cantidad", 0),
                "precio_unitario": float(item.get("precio_unitario", item.get("precio_venta", 0))),
            }
            for item in items
        ]

        fecha = venta.get("fecha", "")
        if hasattr(fecha, "strftime"):
            fecha = fecha.strftime("%Y-%m-%d %H:%M")

        identificacion = f"{str(fecha)[:10]}_VENTA-{venta_id}"

        return await self._png_generator.generar(
            numero=identificacion,
            total=float(venta.get("total", 0.0)),
            fecha=fecha,
            productos=productos,
            nombre_negocio=config.get("nombre_negocio", "Mi Tienda"),
        )
