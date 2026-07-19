# Adaptador: implementa ProductoRepositoryPort usando SQLAlchemy async.
# EXTENDIDO en PR1: agrega stubs de los métodos nuevos (implementación en PR2).
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    CategoriaModel,
    ProductoModel,
)


def _a_entidad(fila: ProductoModel, categoria: str | None = None) -> Producto:
    return Producto(
        id=fila.id,
        codigo=fila.codigo,
        nombre=fila.nombre,
        categoria_id=fila.categoria_id,
        precio=fila.precio,
        precio_compra_actual=fila.precio_compra_actual,
        es_codigo_interno=fila.es_codigo_interno,
        foto_url=fila.foto_url,
        stock=fila.stock,
        stock_minimo=fila.stock_minimo,
        activo=fila.activo,
        categoria=categoria,
        categoria_nombre=categoria,
        creado_por=fila.creado_por,
        creado_por_nombre=fila.creado_por_nombre,
        actualizado_por=fila.actualizado_por,
        actualizado_por_nombre=fila.actualizado_por_nombre,
        created_at=fila.created_at,
        updated_at=fila.updated_at,
        deleted_at=fila.deleted_at,
        deleted_by=fila.deleted_by,
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
            precio_compra_actual=producto.precio_compra_actual,
            es_codigo_interno=producto.es_codigo_interno,
            foto_url=producto.foto_url,
            stock=producto.stock,
            stock_minimo=producto.stock_minimo,
            activo=producto.activo,
            creado_por=producto.creado_por,
            creado_por_nombre=producto.creado_por_nombre,
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
        editables = (
            "codigo", "nombre", "categoria_id", "precio", "precio_compra_actual",
            "stock_minimo", "activo",
        )
        for campo, valor in cambios.items():
            if campo in editables:
                setattr(fila, campo, valor)
        await self._db.flush()
        return await self.buscar_por_id(producto_id)

    # ----- PR1: stubs de métodos nuevos (implementación en PR2) -----

    async def listar_paginado(
        self,
        *,
        search=None,
        categoria_id=None,
        solo_con_stock=False,
        solo_bajo_minimo=False,
        activo=None,
        page=1,
        page_size=20,
    ):
        raise NotImplementedError("Implementado en PR2")

    async def find_bajo_minimo(
        self, *, categoria_id=None, page=1, page_size=20
    ) -> list[Producto]:
        raise NotImplementedError("Implementado en PR2")

    async def find_by_id_for_update(self, producto_id: int) -> Producto | None:
        raise NotImplementedError("Implementado en PR2")

    async def actualizar_general(
        self, producto_id: int, cambios: dict, usuario_id: int, usuario_nombre: str
    ) -> Producto:
        raise NotImplementedError("Implementado en PR2")

    async def actualizar_precio(
        self, producto_id, precio_venta, precio_compra_actual, usuario_id, usuario_nombre
    ):
        raise NotImplementedError("Implementado en PR2")

    async def incrementar_stock_atomic(
        self, producto_id: int, delta: int
    ) -> tuple[bool, int | None]:
        raise NotImplementedError("Implementado en PR2")
