# Puerto explícito hacia el módulo de inventario: solo declara qué se necesita
# (consultar/descontar/reponer stock), no de dónde viene (docs/ARQUITECTURA.md §4).
#
# DECISIÓN (conversada con el equipo): el adaptador NO usa HTTP interno sino la
# misma sesión de BD de la venta (adapters/integrations/sqlalchemy_stock_adapter.py).
# Motivo: RNF-03 exige que venta + descuento de stock sean ATÓMICOS (o pasan ambos
# o ninguno); con una llamada HTTP a otro módulo eso no se puede garantizar.
# El caso de uso solo conoce este puerto: si mañana se separa en servicios, se
# escribe otro adaptador sin tocar la lógica de venta.
from abc import ABC, abstractmethod

from app.modules.modulo_c_ventas.domain.entities import ProductoVendible


class ProductoStockPort(ABC):
    @abstractmethod
    async def obtener_para_venta(self, producto_ids: list[int]) -> dict[int, ProductoVendible]:
        """Datos de venta (nombre, precio, stock) de los productos pedidos."""

    @abstractmethod
    async def descontar_stock(
        self,
        producto_id: int,
        cantidad: int,
        usuario_id: int | None = None,
        usuario_nombre: str = "",
    ) -> bool:
        """Descuenta stock de forma atómica. False si no hay existencias suficientes
        (el stock nunca queda negativo, RF-08). El usuario se usa para dejar el
        asiento en `movimientos_inventario` (D-07)."""

    @abstractmethod
    async def marcar_alerta_stock(self, producto_id: int) -> bool:
        """Marca la alerta de stock mínimo del producto. True solo la primera
        vez, para no repetir el aviso hasta que se reponga (RF-24)."""

    @abstractmethod
    async def reponer_stock(
        self,
        producto_id: int,
        cantidad: int,
        usuario_id: int | None = None,
        usuario_nombre: str = "",
        motivo: str | None = None,
    ) -> None:
        """Devuelve unidades al inventario (anulaciones y devoluciones, RF-22),
        dejando el asiento correspondiente en `movimientos_inventario`."""
