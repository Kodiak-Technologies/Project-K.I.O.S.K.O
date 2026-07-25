# Adaptador: implementa CategoriaRepositoryPort (extendido en PR2).
# Extiende: find_by_id, actualizar, find_by_nombre.
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
        if await self.find_by_nombre(nombre) is not None:
            raise ConflictoError(f"La categoría '{nombre}' ya existe.")
        fila = CategoriaModel(nombre=nombre)
        self._db.add(fila)
        await self._db.flush()
        return _a_entidad(fila)

    async def find_by_id(self, categoria_id: int) -> Categoria | None:
        fila = (
            await self._db.execute(
                select(CategoriaModel).where(CategoriaModel.id == categoria_id)
            )
        ).scalar_one_or_none()
        if fila is None or fila.deleted_at is not None:
            return None
        return _a_entidad(fila)

    async def actualizar(
        self, categoria_id: int, cambios: dict, usuario_id: int | None = None, usuario_nombre: str | None = None
    ) -> Categoria:
        fila = (
            await self._db.execute(
                select(CategoriaModel).where(CategoriaModel.id == categoria_id)
            )
        ).scalar_one()
        if fila.deleted_at is not None:
            from app.shared.kernel.exceptions import NoEncontradoError
            raise NoEncontradoError("Categoría no encontrada.")
        if "nombre" in cambios and cambios["nombre"] is not None:
            nuevo_nombre = cambios["nombre"].strip()
            existente = await self.find_by_nombre(nuevo_nombre)
            if existente is not None and existente.id != categoria_id:
                raise ConflictoError(f"La categoría '{nuevo_nombre}' ya existe.")
            fila.nombre = nuevo_nombre
        if "descripcion" in cambios:
            fila.descripcion = cambios["descripcion"]
        if "activo" in cambios and cambios["activo"] is False:
            # Soft delete via deleted_at
            from datetime import datetime, timezone
            from app.shared.kernel.soft_delete import marcar_borrado
            marcar_borrado(fila, usuario_id or 0)
        await self._db.flush()
        return _a_entidad(fila)

    async def find_by_nombre(self, nombre: str) -> Categoria | None:
        fila = (
            await self._db.execute(
                select(CategoriaModel).where(
                    CategoriaModel.nombre == nombre.strip(),
                    CategoriaModel.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        return _a_entidad(fila) if fila else None
