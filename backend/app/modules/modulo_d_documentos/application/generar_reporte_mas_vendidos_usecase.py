from collections import defaultdict

from app.modules.modulo_d_documentos.domain.entities import TopProducto
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort


class GenerarReporteMasVendidosUseCase:
    def __init__(self, venta_data: VentaDataProviderPort) -> None:
        self._venta_data = venta_data

    async def ejecutar(
        self,
        desde: str,
        hasta: str,
        criterio: str = "unidades",
        categoria_id: int | None = None,
    ) -> list[TopProducto]:
        ventas = await self._venta_data.listar_ventas(desde=desde, hasta=hasta)

        producto_stats: dict[str, dict] = defaultdict(lambda: {"cantidad": 0, "total": 0.0})

        for venta in ventas:
            items = await self._venta_data.obtener_detalle_venta(venta["id"])
            for item in items:
                if categoria_id is not None:
                    if item.get("categoria_id") != categoria_id:
                        continue

                nombre = item.get("nombre", "Desconocido")
                cantidad = item.get("cantidad", 0)
                precio = item.get("precio_unitario", 0)
                producto_stats[nombre]["cantidad"] += cantidad
                producto_stats[nombre]["total"] += cantidad * precio

        key_func = (
            lambda x: x.cantidad if criterio == "unidades" else x.total
        )

        top_productos = sorted(
            [TopProducto(nombre=k, cantidad=v["cantidad"], total=v["total"])
             for k, v in producto_stats.items()],
            key=key_func,
            reverse=True,
        )[:20]

        return top_productos
