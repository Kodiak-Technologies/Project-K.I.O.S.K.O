# Adaptador: implementa CategoriaRepositoryPort usando SQLAlchemy async.
# EXTRAÍDO en PR1 desde `sqlalchemy_producto_repository.py` (D-02 SRP).
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import Categoria
from app.modules.modulo_b_inventario.domain.ports.categoria_repository_port import (
    CategoriaRepositoryPort,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    CategoriaModel,
)
from app.shared.kernel.exceptions import ConflictoError


def _a_entidad(fila: CategoriaModel) -> Categoria:
    return Categoria(
        id=fila.id,
        nombre=fila.nombre,
        descripcion=fila.descripcion,
        creado_por=fila.creado_por,
        creado_por_nombre=fila.creado_por_nombre,
        created_at=fila.created_at,
        updated_at=fila.updated_at,
        deleted_at=fila.deleted_at,
        deleted_by=fila.deleted_by,
    )


class SqlAlchemyCategoriaRepository(CategoriaRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def listar(self) -> list[Categoria]:
        filas = (
            await self._db.execute(
                select(CategoriaModel)
                .where(CategoriaModel.deleted_at.is_(None))
                .order_by(CategoriaModel.nombre)
            )
        ).scalars()
        return [_a_entidad(f) for f in filas]

    async def crear(self, nombre: str) -> Categoria:
        nombre = nombre.strip()
        existente = (
            await self._db.execute(
                select(CategoriaModel).where(
                    CategoriaModel.nombre == nombre,
                    CategoriaModel.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existente is not None:
            raise ConflictoError(f"La categoría '{nombre}' ya existe.")
        fila = CategoriaModel(nombre=nombre)
        self._db.add(fila)
        await self._db.flush()
        return _a_entidad(fila)

    # ----- PR1: stubs de métodos nuevos (implementación en PR2) -----

    async def find_by_id(self, categoria_id: int) -> Categoria | None:
        raise NotImplementedError("Implementado en PR2")

    async def actualizar(self, categoria_id: int, cambios: dict) -> Categoria:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_nombre(self, nombre: str) -> Categoria | None:
        raise NotImplementedError("Implementado en PR2")
