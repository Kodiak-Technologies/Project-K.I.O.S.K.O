# Puerto: contrato para persistir/consultar productos del catálogo.
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import Producto


class ProductoRepositoryPort(ABC):
    @abstractmethod
    async def listar(self, busqueda: str | None = None) -> list[Producto]:
        """Productos no eliminados; `busqueda` filtra por nombre o código."""

    @abstractmethod
    async def buscar_por_id(self, producto_id: int) -> Producto | None: ...

    @abstractmethod
    async def buscar_por_codigo(self, codigo: str) -> Producto | None: ...

    @abstractmethod
    async def crear(self, producto: Producto) -> Producto: ...

    @abstractmethod
    async def actualizar(self, producto_id: int, cambios: dict) -> Producto: ...
