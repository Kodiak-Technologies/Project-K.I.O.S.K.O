from typing import Protocol


class VentaDataProviderPort(Protocol):
    async def obtener_venta(self, venta_id: int) -> dict | None:
        """Retorna los datos de una venta por su ID. None si no existe."""
        ...

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        """Retorna la lista de ventas en el rango de fechas dado."""
        ...

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        """Retorna los items/productos de una venta específica."""
        ...
