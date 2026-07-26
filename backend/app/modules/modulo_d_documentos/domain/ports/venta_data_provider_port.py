from typing import Protocol


class VentaDataProviderPort(Protocol):
    async def obtener_venta(self, venta_id: int) -> dict | None:
        """Retorna los datos de una venta por su ID. None si no existe."""
        ...

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        """Retorna TODAS las ventas del rango.

        Sólo para quien realmente necesita el rango entero: los reportes
        (que agregan sobre todo el período) y el ZIP de notas. Para mostrar
        una página usá `listar_ventas_paginado`.
        """
        ...

    async def listar_ventas_paginado(
        self,
        desde: str | None = None,
        hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """(ventas de esa página, total del rango).

        Trae sólo la página pedida: el costo no depende del tamaño del
        histórico, a diferencia de recortar en memoria lo que devuelve
        `listar_ventas`.
        """
        ...

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        """Retorna los items/productos de una venta específica."""
        ...

    async def obtener_pagos_venta(self, venta_id: int) -> list[dict]:
        """Retorna los pagos de una venta específica."""
        ...
