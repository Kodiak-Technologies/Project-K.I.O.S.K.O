from collections import defaultdict

from app.modules.modulo_d_documentos.domain.entities import ResumenReporte, TopProducto
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort
from app.modules.modulo_d_documentos.domain.ports.egresos_data_provider_port import EgresosDataProviderPort
from app.modules.modulo_d_documentos.domain.ports.metodo_pago_provider_port import MetodoPagoProviderPort


class GenerarReporteVentasUseCase:
    def __init__(
        self,
        venta_data: VentaDataProviderPort,
        egresos_data: EgresosDataProviderPort | None = None,
        metodo_pago_data: MetodoPagoProviderPort | None = None,
    ) -> None:
        self._venta_data = venta_data
        self._egresos_data = egresos_data
        self._metodo_pago_data = metodo_pago_data

    async def ejecutar(self, desde: str, hasta: str) -> ResumenReporte:
        ventas = await self._venta_data.listar_ventas(desde=desde, hasta=hasta)

        total_vendido = sum(v.get("total", 0) for v in ventas)
        numero_ventas = len(ventas)

        producto_stats: dict[str, dict] = defaultdict(lambda: {"cantidad": 0, "total": 0.0})

        for venta in ventas:
            items = await self._venta_data.obtener_detalle_venta(venta["id"])
            for item in items:
                nombre = item.get("nombre", "Desconocido")
                cantidad = item.get("cantidad", 0)
                precio = item.get("precio_unitario", 0)
                producto_stats[nombre]["cantidad"] += cantidad
                producto_stats[nombre]["total"] += cantidad * precio

        top_productos = sorted(
            [TopProducto(nombre=k, cantidad=v["cantidad"], total=v["total"])
             for k, v in producto_stats.items()],
            key=lambda x: x.total,
            reverse=True,
        )[:10]

        total_egresos = 0.0
        if self._egresos_data:
            total_egresos = await self._egresos_data.total_egresos(desde, hasta)

        metodos_pago: dict[str, float] = {}
        if self._metodo_pago_data:
            metodos_pago = await self._metodo_pago_data.desglose_por_metodo(desde, hasta)

        resumen = ResumenReporte(
            desde=desde,
            hasta=hasta,
            total_vendido=total_vendido,
            total_egresos=total_egresos,
            numero_ventas=numero_ventas,
            top_productos=top_productos,
            metodos_pago=metodos_pago,
        )
        resumen.calcular_ticket_promedio()

        return resumen
