# Adaptador: implementa ProductoRepositoryPort y CategoriaRepositoryPort usando SQLAlchemy.
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import Categoria, Producto
from app.modules.modulo_b_inventario.domain.ports.categoria_repository_port import (
    CategoriaRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    CategoriaModel,
    ProductoModel,
)
from app.shared.kernel.exceptions import ConflictoError


def _a_entidad(fila: ProductoModel, categoria: str | None = None) -> Producto:
    return Producto(
        id=fila.id,
        codigo=fila.codigo,
        nombre=fila.nombre,
        categoria_id=fila.categoria_id,
        precio=fila.precio,
        stock=fila.stock,
        stock_minimo=fila.stock_minimo,
        activo=fila.activo,
        categoria=categoria,
        created_at=fila.created_at,
    )


class SqlAlchemyProductoRepository(ProductoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    def _consulta_base(self):
        # LEFT JOIN para traer el nombre de la categoría en la misma consulta.
        return (
            select(ProductoModel, CategoriaModel.nombre)
            .join(CategoriaModel, ProductoModel.categoria_id == CategoriaModel.id, isouter=True)
            .where(ProductoModel.deleted_at.is_(None))
        )

    async def listar(self, busqueda: str | None = None) -> list[Producto]:
        consulta = self._consulta_base().order_by(ProductoModel.nombre)
        if busqueda:
            patron = f"%{busqueda.strip()}%"
            consulta = consulta.where(
                or_(ProductoModel.nombre.ilike(patron), ProductoModel.codigo.ilike(patron))
            )
        filas = (await self._db.execute(consulta)).all()
        return [_a_entidad(fila, nombre_cat) for fila, nombre_cat in filas]

    async def buscar_por_id(self, producto_id: int) -> Producto | None:
        fila = (
            await self._db.execute(self._consulta_base().where(ProductoModel.id == producto_id))
        ).first()
        return _a_entidad(fila[0], fila[1]) if fila else None

    async def buscar_por_codigo(self, codigo: str) -> Producto | None:
        fila = (
            await self._db.execute(self._consulta_base().where(ProductoModel.codigo == codigo))
        ).first()
        return _a_entidad(fila[0], fila[1]) if fila else None

    async def crear(self, producto: Producto) -> Producto:
        fila = ProductoModel(
            codigo=producto.codigo,
            nombre=producto.nombre,
            categoria_id=producto.categoria_id,
            precio=producto.precio,
            stock=producto.stock,
            stock_minimo=producto.stock_minimo,
            activo=producto.activo,
        )
        self._db.add(fila)
        await self._db.flush()
        return await self.buscar_por_id(fila.id)

    async def actualizar(self, producto_id: int, cambios: dict) -> Producto:
        fila = (
            await self._db.execute(select(ProductoModel).where(ProductoModel.id == producto_id))
        ).scalar_one()
        # `cambios` viene con exclude_unset: toda clave presente es intencional
        # (categoria_id=None significa "quitar la categoría").
        editables = ("codigo", "nombre", "categoria_id", "precio", "stock_minimo", "activo")
        for campo, valor in cambios.items():
            if campo in editables:
                setattr(fila, campo, valor)
        await self._db.flush()
        return await self.buscar_por_id(producto_id)


class SqlAlchemyCategoriaRepository(CategoriaRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def listar(self) -> list[Categoria]:
        filas = (
            await self._db.execute(select(CategoriaModel).order_by(CategoriaModel.nombre))
        ).scalars()
        return [Categoria(id=f.id, nombre=f.nombre) for f in filas]

    async def crear(self, nombre: str) -> Categoria:
        nombre = nombre.strip()
        existente = (
            await self._db.execute(select(CategoriaModel).where(CategoriaModel.nombre == nombre))
        ).scalar_one_or_none()
        if existente is not None:
            raise ConflictoError(f"La categoría '{nombre}' ya existe.")
        fila = CategoriaModel(nombre=nombre)
        self._db.add(fila)
        await self._db.flush()
        return Categoria(id=fila.id, nombre=fila.nombre)
