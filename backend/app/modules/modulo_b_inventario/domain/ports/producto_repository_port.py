# Puerto: contrato para persistir/consultar productos del catálogo.
# EXTENDIDO en PR1: agrega métodos para paginación, lock pesimista, actualización
# de precio, edición general y actualización atómica de stock.
from abc import ABC, abstractmethod
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.entities import Producto


class ProductoRepositoryPort(ABC):
    # ----- Métodos del skeleton original (compatibilidad) -----

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

    # ----- Métodos nuevos (PR1: declarados como abstractos, implementación en PR2) -----

    @abstractmethod
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
        """Listado paginado con filtros. Devuelve (items, total)."""

    @abstractmethod
    async def find_bajo_minimo(
        self,
        *,
        categoria_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Producto]:
        """Productos activos con stock <= stock_minimo. Faltante se calcula en el use case."""

    @abstractmethod
    async def find_by_id_for_update(self, producto_id: int) -> Producto | None:
        """SELECT ... FOR UPDATE; se usa en cambiar precio y aprobar ingreso."""

    @abstractmethod
    async def actualizar_general(
        self, producto_id: int, cambios: dict, usuario_id: int, usuario_nombre: str
    ) -> Producto:
        """Edita campos no-precio (nombre, categoría, stock_minimo, activo).
        El caller debe haber rechazado `precio`/`precio_compra_actual` con 422."""

    @abstractmethod
    async def actualizar_precio(
        self,
        producto_id: int,
        precio_venta: Decimal | None,
        precio_compra_actual: Decimal | None,
        usuario_id: int,
        usuario_nombre: str,
    ) -> tuple[Producto, list]:
        """Cambia precios y APPEND en historial_precios. Devuelve (producto_actualizado, filas_historial)."""

    @abstractmethod
    async def incrementar_stock_atomic(
        self, producto_id: int, delta: int
    ) -> tuple[bool, int | None]:
        """UPDATE atómico: stock = stock + :delta WHERE id=:id AND stock >= -delta
        AND deleted_at IS NULL. Devuelve (ok, stock_actual).
        `delta` positivo = entrada, negativo = salida. Si `delta` es negativo,
        exige `stock >= |delta|` (rechaza 0 filas → 409 'Stock insuficiente')."""
