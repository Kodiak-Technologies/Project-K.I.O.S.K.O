from typing import Protocol


class MetodoPagoProviderPort(Protocol):
    async def desglose_por_metodo(self, desde: str, hasta: str) -> dict[str, float]:
        """Retorna el desglose de ventas por método de pago.
        Ejemplo: {"EFECTIVO": 850.00, "YAPE": 320.00, "PLIN": 180.00}
        """
        ...
