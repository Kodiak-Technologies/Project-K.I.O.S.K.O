# Adaptador: implementa ProductoRepositoryPort usando SQLAlchemy async.
# Implementación completa de PR2: incluye listar_paginado, find_bajo_minimo,
# find_by_id_for_update, actualizar_general, actualizar_precio, incrementar_stock_atomic.
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_b_inventario.domain.entities import (
    HistorialPrecio,
    Producto,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import TipoPrecio
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    CategoriaModel,
    HistorialPrecioModel,
    ProductoModel,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
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
        alerta_stock_notificada=fila.alerta_stock_notificada,
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


def _historial_a_entidad(fila: HistorialPrecioModel) -> HistorialPrecio:
    return HistorialPrecio(
        id=fila.id,
        producto_id=fila.producto_id,
        precio_nuevo=fila.precio_nuevo,
        tipo_precio=TipoPrecio(fila.tipo_precio),
        modificado_por=fila.modificado_por,
        modificado_por_nombre=fila.modificado_por_nombre,
        precio_anterior=fila.precio_anterior,
        created_at=fila.created_at,
    )


class SqlAlchemyProductoRepository(ProductoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    def _consulta_base(self):
        return (
            select(ProductoModel, CategoriaModel.nombre)
            .join(
                CategoriaModel,
                ProductoModel.categoria_id == CategoriaModel.id,
                isouter=True,
            )
            .where(ProductoModel.deleted_at.is_(None))
        )

    async def listar(
        self, busqueda: str | None = None
    ) -> list[Producto]:
        consulta = self._consulta_base().order_by(ProductoModel.nombre)
        if busqueda:
            patron = f"%{busqueda.strip()}%"
            consulta = consulta.where(
                or_(
                    ProductoModel.nombre.ilike(patron),
                    ProductoModel.codigo.ilike(patron),
                )
            )
        filas = (await self._db.execute(consulta)).all()
        return [_a_entidad(f, nombre_cat) for f, nombre_cat in filas]

    async def buscar_por_id(self, producto_id: int) -> Producto | None:
        fila = (
            await self._db.execute(
                self._consulta_base().where(ProductoModel.id == producto_id)
            )
        ).first()
        return _a_entidad(fila[0], fila[1]) if fila else None

    async def buscar_por_codigo(self, codigo: str) -> Producto | None:
        fila = (
            await self._db.execute(
                self._consulta_base().where(ProductoModel.codigo == codigo)
            )
        ).first()
        return _a_entidad(fila[0], fila[1]) if fila else None

    async def existe_codigo(self, codigo: str) -> bool:
        # El UNIQUE de `productos.codigo` es global (no excluye borrados
        # lógicos): para validar unicidad hay que mirar TAMBIÉN los borrados,
        # si no el INSERT explota con IntegrityError (500) en vez de 409.
        fila = (
            await self._db.execute(
                select(ProductoModel.id).where(ProductoModel.codigo == codigo)
            )
        ).first()
        return fila is not None

    async def siguiente_correlativo_interno(self, prefijo: str) -> int:
        # Lock consultivo por prefijo: serializa la generación del correlativo
        # entre transacciones concurrentes (se libera al terminar la tx). Sin
        # esto, dos altas simultáneas calculan el mismo número y una explota
        # con violación de UNIQUE.
        try:
            await self._db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:clave))"),
                {"clave": f"producto_codigo_interno:{prefijo}"},
            )
        except Exception:  # noqa: BLE001 - motores sin advisory locks
            pass
        codigos = (
            (
                await self._db.execute(
                    select(ProductoModel.codigo).where(
                        ProductoModel.codigo.like(f"{prefijo}-%")
                    )
                )
            )
            .scalars()
            .all()
        )
        maximo = 0
        for codigo in codigos:
            sufijo = codigo.split("-", 1)[1] if "-" in codigo else ""
            if sufijo.isdigit():
                maximo = max(maximo, int(sufijo))
        return maximo + 1

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
        return await self.buscar_por_id(fila.id)  # type: ignore[return-value]

    async def actualizar(self, producto_id: int, cambios: dict) -> Producto:
        # Reutilizado para compatibilidad: edición general
        return await self.actualizar_general(producto_id, cambios, 0, "system")

    # ----- PR2: implementaciones reales -----

    async def listar_paginado(
        self,
        *,
        search: str | None = None,
        categoria_id: int | None = None,
        solo_con_stock: bool = False,
        solo_bajo_minimo: bool = False,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Producto], int]:
        filtros: list[Any] = [ProductoModel.deleted_at.is_(None)]
        if categoria_id is not None:
            filtros.append(ProductoModel.categoria_id == categoria_id)
        if solo_con_stock:
            filtros.append(ProductoModel.stock > 0)
        if solo_bajo_minimo:
            # `stock_minimo = 0` = sin umbral definido → no cuenta como "por reponer".
            filtros.append(ProductoModel.stock_minimo > 0)
            filtros.append(ProductoModel.stock <= ProductoModel.stock_minimo)
        if activo is not None:
            filtros.append(ProductoModel.activo == activo)
        if search:
            patron = f"%{search.strip()}%"
            filtros.append(
                or_(
                    ProductoModel.nombre.ilike(patron),
                    ProductoModel.codigo.ilike(patron),
                )
            )

        total = (
            await self._db.execute(
                select(func.count())
                .select_from(ProductoModel)
                .where(*filtros)
            )
        ).scalar_one()
        filas = (
            (
                await self._db.execute(
                    select(ProductoModel, CategoriaModel.nombre)
                    .join(
                        CategoriaModel,
                        ProductoModel.categoria_id == CategoriaModel.id,
                        isouter=True,
                    )
                    .where(*filtros)
                    .order_by(ProductoModel.nombre)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return [_a_entidad(f, nombre_cat) for f, nombre_cat in filas], total

    async def find_bajo_minimo(
        self,
        *,
        categoria_id: int | None = None,
        solo_no_notificadas: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Producto]:
        filtros: list[Any] = [
            ProductoModel.deleted_at.is_(None),
            ProductoModel.activo.is_(True),
            ProductoModel.stock_minimo > 0,
            ProductoModel.stock <= ProductoModel.stock_minimo,
        ]
        if categoria_id is not None:
            filtros.append(ProductoModel.categoria_id == categoria_id)
        if solo_no_notificadas:
            # HU-B13: alerta única por producto hasta su reposición.
            filtros.append(ProductoModel.alerta_stock_notificada.is_(False))
        filas = (
            (
                await self._db.execute(
                    select(ProductoModel, CategoriaModel.nombre)
                    .join(
                        CategoriaModel,
                        ProductoModel.categoria_id == CategoriaModel.id,
                        isouter=True,
                    )
                    .where(*filtros)
                    # Orden por faltante DESC
                    .order_by(
                        (ProductoModel.stock_minimo - ProductoModel.stock).desc(),
                        ProductoModel.nombre,
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return [_a_entidad(f, nombre_cat) for f, nombre_cat in filas]

    async def find_by_id_for_update(
        self, producto_id: int
    ) -> Producto | None:
        fila = (
            await self._db.execute(
                select(ProductoModel, CategoriaModel.nombre)
                .join(
                    CategoriaModel,
                    ProductoModel.categoria_id == CategoriaModel.id,
                    isouter=True,
                )
                .where(
                    ProductoModel.id == producto_id,
                    ProductoModel.deleted_at.is_(None),
                )
                .with_for_update()
            )
        ).first()
        return _a_entidad(fila[0], fila[1]) if fila else None

    async def actualizar_general(
        self,
        producto_id: int,
        cambios: dict,
        usuario_id: int,
        usuario_nombre: str,
    ) -> Producto:
        # Rechaza cambios de precio en edición general (D-T05: 422)
        if "precio" in cambios or "precio_compra_actual" in cambios:
            raise ValidacionError(
                "Use PATCH /productos/{id}/precio para cambiar precios."
            )
        fila = (
            await self._db.execute(
                select(ProductoModel).where(ProductoModel.id == producto_id)
            )
        ).scalar_one()
        if fila.deleted_at is not None:
            raise NoEncontradoError("Producto no encontrado.")

        # Validar codigo duplicado si se intenta cambiar
        if "codigo" in cambios and cambios["codigo"] is not None:
            nuevo = cambios["codigo"].strip()
            if nuevo != fila.codigo:
                existente = (
                    await self._db.execute(
                        select(ProductoModel).where(
                            ProductoModel.codigo == nuevo,
                            ProductoModel.deleted_at.is_(None),
                            ProductoModel.id != producto_id,
                        )
                    )
                ).scalar_one_or_none()
                if existente is not None:
                    raise ConflictoError(
                        f"Ya existe un producto con el código '{nuevo}'."
                    )
                fila.codigo = nuevo

        editables = {
            "nombre",
            "categoria_id",
            "stock_minimo",
            "activo",
            "es_codigo_interno",
            "foto_url",
        }
        # Campos que aceptan NULL explícito: mandar `categoria_id: null` debe
        # DESASIGNAR la categoría (antes el None se descartaba en silencio).
        anulables = {"categoria_id", "foto_url"}
        for campo, valor in cambios.items():
            if campo not in editables:
                continue
            if valor is None and campo not in anulables:
                continue
            setattr(fila, campo, valor)
        # Si el stock quedó por encima del nuevo mínimo, rearmamos la alerta.
        if fila.stock > fila.stock_minimo:
            fila.alerta_stock_notificada = False
        fila.actualizado_por = usuario_id
        fila.actualizado_por_nombre = usuario_nombre
        await self._db.flush()
        return await self.buscar_por_id(producto_id)  # type: ignore[return-value]

    async def actualizar_precio(
        self,
        producto_id: int,
        precio_venta: Decimal | None,
        precio_compra_actual: Decimal | None,
        usuario_id: int,
        usuario_nombre: str,
    ) -> tuple[Producto, list[HistorialPrecio]]:
        # SELECT ... FOR UPDATE para evitar race conditions
        fila = (
            await self._db.execute(
                select(ProductoModel)
                .where(
                    ProductoModel.id == producto_id,
                    ProductoModel.deleted_at.is_(None),
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if fila is None:
            raise NoEncontradoError("Producto no encontrado.")

        filas_historial: list[HistorialPrecio] = []
        # Historial rows staged for flush. Each HistorialPrecioModel is added to
        # the session, but the domain entity MUST be built AFTER `flush()` so
        # the DB-assigned `id` and `created_at` are populated. Building before
        # flush would yield `id=None` and break the strict `id: int` contract
        # in `HistorialPrecioResponse`, surfacing as HTTP 500.
        filas_historial_pendientes: list[HistorialPrecioModel] = []

        # Precio de venta
        if precio_venta is not None and Decimal(str(precio_venta)) != fila.precio:
            anterior = fila.precio
            nuevo = Decimal(str(precio_venta))
            hist = HistorialPrecioModel(
                producto_id=producto_id,
                precio_anterior=anterior,
                precio_nuevo=nuevo,
                tipo_precio="venta",
                modificado_por=usuario_id,
                modificado_por_nombre=usuario_nombre,
            )
            self._db.add(hist)
            filas_historial_pendientes.append(hist)
            fila.precio = nuevo

        # Precio de compra
        if (
            precio_compra_actual is not None
            and Decimal(str(precio_compra_actual)) != fila.precio_compra_actual
        ):
            anterior = fila.precio_compra_actual
            nuevo = Decimal(str(precio_compra_actual))
            hist = HistorialPrecioModel(
                producto_id=producto_id,
                precio_anterior=anterior,
                precio_nuevo=nuevo,
                tipo_precio="compra",
                modificado_por=usuario_id,
                modificado_por_nombre=usuario_nombre,
            )
            self._db.add(hist)
            filas_historial_pendientes.append(hist)
            fila.precio_compra_actual = nuevo

        fila.actualizado_por = usuario_id
        fila.actualizado_por_nombre = usuario_nombre
        await self._db.flush()
        # Build domain entities from the flushed models so `id` is the real
        # DB-assigned value. Matches the pattern in
        # `sqlalchemy_pago_proveedor_repository.py:54-58` and
        # `sqlalchemy_historial_precio_repository.py:48-51`.
        filas_historial = [_historial_a_entidad(h) for h in filas_historial_pendientes]
        producto = await self.buscar_por_id(producto_id)  # type: ignore[return-value]
        return producto, filas_historial

    async def incrementar_stock_atomic(
        self, producto_id: int, delta: int
    ) -> tuple[bool, int | None]:
        # El CHECK `stock >= 0` se refuerza con WHERE stock >= -delta
        resultado = await self._db.execute(
            update(ProductoModel)
            .where(
                ProductoModel.id == producto_id,
                ProductoModel.deleted_at.is_(None),
                ProductoModel.stock >= -delta,
            )
            .values(stock=ProductoModel.stock + delta)
        )
        if (resultado.rowcount or 0) == 0:
            return (False, None)
        # HU-B13: al reponer por encima del mínimo, la alerta se rearma sola.
        if delta > 0:
            await self._db.execute(
                update(ProductoModel)
                .where(
                    ProductoModel.id == producto_id,
                    ProductoModel.stock > ProductoModel.stock_minimo,
                )
                .values(alerta_stock_notificada=False)
            )
        fila = (
            await self._db.execute(
                select(ProductoModel.stock).where(ProductoModel.id == producto_id)
            )
        ).scalar_one()
        return (True, int(fila))

    async def marcar_alertas_notificadas(self, producto_ids: list[int]) -> int:
        """HU-B13: marca los productos cuya alerta de stock mínimo ya se avisó."""
        if not producto_ids:
            return 0
        resultado = await self._db.execute(
            update(ProductoModel)
            .where(
                ProductoModel.id.in_(producto_ids),
                ProductoModel.deleted_at.is_(None),
            )
            .values(alerta_stock_notificada=True)
        )
        return resultado.rowcount or 0
