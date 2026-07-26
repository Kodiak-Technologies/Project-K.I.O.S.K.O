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

        # Una venta ANULADA se revirtió por completo (repuso stock y devolvió la
        # plata): no es venta. Antes sumaba igual al total y al top de productos.
        ventas = [v for v in ventas if str(v.get("estado", "")).upper() != "ANULADA"]
        numero_ventas = len(ventas)

        producto_stats: dict[str, dict] = defaultdict(lambda: {"cantidad": 0, "total": 0.0})

        # El total sale de las líneas netas (cantidad − devuelta), no del total
        # bruto de la venta: así una devolución parcial se refleja en el reporte.
        total_vendido = 0.0
        total_devuelto = 0.0
        for venta in ventas:
            items = await self._venta_data.obtener_detalle_venta(venta["id"])
            if not items:
                # Sin detalle disponible, el total de la venta es lo mejor que hay.
                total_vendido += float(venta.get("total", 0))
                continue
            for item in items:
                nombre = item.get("nombre", "Desconocido")
                precio = item.get("precio_unitario", 0)
                devueltas = item.get("cantidad_devuelta", 0)
                total_devuelto += devueltas * precio
                cantidad = item.get("cantidad", 0) - devueltas
                if cantidad <= 0:
                    continue
                producto_stats[nombre]["cantidad"] += cantidad
                producto_stats[nombre]["total"] += cantidad * precio
                total_vendido += cantidad * precio

        top_productos = sorted(
            [TopProducto(nombre=k, cantidad=v["cantidad"], total=v["total"])
             for k, v in producto_stats.items()],
            key=lambda x: x.total,
            reverse=True,
        )[:10]

        total_egresos = 0.0
        if self._egresos_data:
            total_egresos = await self._egresos_data.total_egresos(desde, hasta)

        # Nota: `metodos_pago` es lo COBRADO por método (de `pagos_venta`); las
        # devoluciones tienen su propio rastro de efectivo, por eso puede no
        # cuadrar exactamente contra el neto vendido cuando hubo devoluciones.
        metodos_pago: dict[str, float] = {}
        if self._metodo_pago_data:
            metodos_pago = await self._metodo_pago_data.desglose_por_metodo(desde, hasta)

        resumen = ResumenReporte(
            desde=desde,
            hasta=hasta,
            total_vendido=total_vendido,
            total_devuelto=total_devuelto,
            total_egresos=total_egresos,
            numero_ventas=numero_ventas,
            top_productos=top_productos,
            metodos_pago=metodos_pago,
        )
        resumen.calcular_ticket_promedio()

        return resumen
