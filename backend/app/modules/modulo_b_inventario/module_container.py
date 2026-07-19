# Wiring del módulo: arma los casos de uso con sus adaptadores concretos (SQLAlchemy).
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.application.actualizar_producto_usecase import (
    ActualizarProductoUseCase,
)
from app.modules.modulo_b_inventario.application.crear_producto_usecase import CrearProductoUseCase
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_producto_repository import (
    SqlAlchemyCategoriaRepository,
    SqlAlchemyProductoRepository,
)


def crear_producto_usecase(db: AsyncSession) -> CrearProductoUseCase:
    return CrearProductoUseCase(SqlAlchemyProductoRepository(db))


def actualizar_producto_usecase(db: AsyncSession) -> ActualizarProductoUseCase:
    return ActualizarProductoUseCase(SqlAlchemyProductoRepository(db))


def producto_repository(db: AsyncSession) -> SqlAlchemyProductoRepository:
    return SqlAlchemyProductoRepository(db)


def categoria_repository(db: AsyncSession) -> SqlAlchemyCategoriaRepository:
    return SqlAlchemyCategoriaRepository(db)
