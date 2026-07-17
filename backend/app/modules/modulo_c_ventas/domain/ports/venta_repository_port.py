# Puerto: contrato para persistir/consultar ventas y sus detalles.
from abc import ABC, abstractmethod
from datetime import date

from app.modules.modulo_c_ventas.domain.entities import Venta


class VentaRepositoryPort(ABC):
    @abstractmethod
    async def crear(self, venta: Venta) -> Venta: ...

    @abstractmethod
    async def buscar_por_id(self, venta_id: int) -> Venta | None: ...

    @abstractmethod
    async def listar(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        turno_id: int | None = None,
    ) -> list[Venta]:
        """Ventas más recientes primero, con sus detalles."""

    @abstractmethod
    async def actualizar_estado(
        self, venta_id: int, estado: str, motivo: str | None = None
    ) -> None: ...
