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
    async def existe_codigo(self, codigo: str) -> bool:
        """True si el código ya está tomado, INCLUYENDO productos borrados
        lógicamente (el UNIQUE de la tabla no distingue)."""

    @abstractmethod
    async def siguiente_correlativo_interno(self, prefijo: str) -> int:
        """Siguiente correlativo libre para códigos internos `PREFIJO-NNN`
        (HU-B03). Debe serializar llamadas concurrentes."""

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
        sin_stock: bool = False,
        precio_min: Decimal | None = None,
        precio_max: Decimal | None = None,
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
        solo_no_notificadas: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Producto]:
        """Productos activos con `stock_minimo > 0` y stock <= stock_minimo.
        El faltante se calcula en el use case. Con `solo_no_notificadas=True`
        devuelve solo los que aún no dispararon su alerta (HU-B13)."""

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
    async def eliminar(self, producto_id: int, usuario_id: int) -> Producto:
        """Borrado lógico (`deleted_at`/`deleted_by`) + `activo = False`.
        Nunca físico: el histórico referencia al producto con RESTRICT."""

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
        exige `stock >= |delta|` (rechaza 0 filas → 409 'Stock insuficiente').
        Al reponer por encima del mínimo rearma la alerta de stock (HU-B13)."""

    @abstractmethod
    async def marcar_alerta_si_nueva(self, producto_id: int) -> bool:
        """Marca la alerta de stock mínimo y devuelve True solo la primera vez
        (candado de la alerta única, HU-B13)."""

    @abstractmethod
    async def marcar_alertas_notificadas(self, producto_ids: list[int]) -> int:
        """HU-B13: marca la alerta de stock mínimo como ya avisada. Se rearma
        sola cuando el producto se repone por encima del mínimo."""
