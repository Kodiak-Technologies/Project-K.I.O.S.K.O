# Puerto: contrato para persistir/consultar categorías del catálogo.
# EXTENDIDO en PR1: agrega find_by_id, actualizar, find_by_nombre.
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import Categoria


class CategoriaRepositoryPort(ABC):
    # ----- Métodos del skeleton original (compatibilidad) -----

    @abstractmethod
    async def listar(self) -> list[Categoria]: ...

    @abstractmethod
    async def crear(self, nombre: str) -> Categoria: ...

    # ----- Métodos nuevos (PR1: declarados como abstractos, implementación en PR2) -----

    @abstractmethod
    async def find_by_id(self, categoria_id: int) -> Categoria | None: ...

    @abstractmethod
    async def actualizar(
        self,
        categoria_id: int,
        cambios: dict,
        usuario_id: int | None = None,
        usuario_nombre: str | None = None,
    ) -> Categoria:
        """Edita nombre y/o descripción. Valida unicidad de nombre si cambia."""

    @abstractmethod
    async def find_by_nombre(self, nombre: str) -> Categoria | None:
        """Búsqueda por nombre (case-sensitive). Usado para validar unicidad al crear/editar."""
