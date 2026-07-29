from typing import Protocol


class EgresosDataProviderPort(Protocol):
    async def obtener_egresos(self, desde: str, hasta: str) -> list[dict]:
        """Retorna la lista de egresos en el rango de fechas dado."""
        ...

    async def total_egresos(self, desde: str, hasta: str) -> float:
        """Retorna el total de egresos en el rango de fechas dado."""
        ...

    async def costo_por_proveedor(self, desde: str, hasta: str) -> list[dict]:
        """Costo de mercadería agrupado por proveedor, de mayor a menor.

        Cada item: `{proveedor, monto, unidades, ingresos}`. Las solicitudes sin
        proveedor asignado se agrupan bajo "Sin proveedor" en vez de quedar
        fuera: si no, el total por proveedor no cuadraría con el total de
        egresos y no habría forma de notar el faltante.
        """
        ...
