from typing import Protocol


class EgresosDataProviderPort(Protocol):
    async def obtener_egresos(self, desde: str, hasta: str) -> list[dict]:
        """Retorna la lista de egresos en el rango de fechas dado."""
        ...

    async def total_egresos(self, desde: str, hasta: str) -> float:
        """Retorna el total de egresos en el rango de fechas dado."""
        ...
