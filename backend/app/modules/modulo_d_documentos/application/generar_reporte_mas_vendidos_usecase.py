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
        orden: str = "mayor",
    ) -> list[TopProducto]:
        ventas = await self._venta_data.listar_ventas(desde=desde, hasta=hasta)
        # Las anuladas no se vendieron (mismo criterio que el resumen).
        ventas = [v for v in ventas if str(v.get("estado", "")).upper() != "ANULADA"]

        # Se agrupa por `producto_id`, NO por nombre: dos productos distintos
        # pueden llamarse igual y antes se sumaban como si fueran uno solo.
        # El nombre se guarda aparte, sólo para mostrar.
        producto_stats: dict[int, dict] = defaultdict(
            lambda: {"cantidad": 0, "total": 0.0, "nombre": "Desconocido", "venta": -1}
        )

        for venta in ventas:
            items = venta.get("items") or []
            for item in items:
                if categoria_id is not None:
                    if item.get("categoria_id") != categoria_id:
                        continue

                # Lo devuelto volvió al stock: no cuenta como vendido.
                cantidad = item.get("cantidad", 0) - item.get("cantidad_devuelta", 0)
                if cantidad <= 0:
                    continue
                precio = item.get("precio_unitario", 0)
                fila = producto_stats[item.get("producto_id")]
                fila["cantidad"] += cantidad
                fila["total"] += cantidad * precio
                # `detalles_venta` guarda el nombre del momento de la venta: si
                # el producto se renombró, se muestra el de la venta más
                # reciente. Se compara por id de venta (monotónico) en vez de
                # confiar en el orden en que llegan.
                if venta["id"] > fila["venta"]:
                    fila["venta"] = venta["id"]
                    fila["nombre"] = item.get("nombre", fila["nombre"])

        key_func = (
            lambda x: x.cantidad if criterio == "unidades" else x.total
        )

        top_productos = sorted(
            [TopProducto(nombre=v["nombre"], cantidad=v["cantidad"], total=v["total"])
             for v in producto_stats.values()],
            key=key_func,
            reverse=(orden == "mayor"),
        )[:20]

        return top_productos
