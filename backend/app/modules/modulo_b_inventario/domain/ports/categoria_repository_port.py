# Puerto: contrato para persistir/consultar categorías del catálogo.
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import Categoria


class CategoriaRepositoryPort(ABC):
    @abstractmethod
    async def listar(self) -> list[Categoria]: ...

    @abstractmethod
    async def crear(self, nombre: str) -> Categoria: ...
