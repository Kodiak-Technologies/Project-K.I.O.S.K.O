# Mocks compartidos para tests unitarios del Módulo B.
# Patrón espejo de `backend/tests/modulo_d_documentos/test_usecases.py`:
# los `Mock*` cumplen el contrato del Port sin usar `unittest.mock.MagicMock`
# (excepto `make_auditoria_mock` para `RegistrarAuditoriaUseCase`, que es una
# dependencia cross-module sin estado — único `AsyncMock` permitido por CN-6).
#
# Disciplina Strict TDD: cada `Mock*` implementa SOLO los métodos del Port
# usados por los use cases en scope. Métodos no declarados levantan
# `NotImplementedError("Mock no configurado para X — drift de Port")` para
# que cualquier cambio de firma del Port haga fallar el test de inmediato
# (señal correcta: un test que llama un método que no existe debe romperse).
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

from app.modules.modulo_b_inventario.domain.entities import (
    Categoria,
    HistorialPrecio,
    MovimientoInventario,
    PagoProveedor,
    Producto,
    Proveedor,
    SolicitudIngreso,
    DetalleSolicitud,
)


# =============================================================================
# Producto
# =============================================================================


class MockProductoRepository:
    """Mock del `ProductoRepositoryPort` con estado en memoria.

    Atributos públicos útiles para aserciones del test:
      - `crear_call_count`, `crear_last_producto`
      - `actualizar_precio_return_value`: tupla `(producto, [filas_hist])`
      - `incrementar_stock_atomic_return_value`: tupla `(ok, stock_actual)`
    """

    def __init__(self) -> None:
        self._productos: dict[int, Producto] = {}
        self._contador = 0
        self.crear_call_count = 0
        self.crear_last_producto: Producto | None = None
        self.actualizar_precio_return_value: tuple[Producto, list] | None = None
        self.incrementar_stock_atomic_return_value: tuple[bool, int | None] = (True, 10)
        self._buscar_por_codigo_retorno: dict[str, Producto | None] = {}

    async def buscar_por_codigo(self, codigo: str) -> Producto | None:
        if codigo in self._buscar_por_codigo_retorno:
            return self._buscar_por_codigo_retorno[codigo]
        for p in self._productos.values():
            if p.codigo == codigo:
                return p
        return None

    def set_buscar_por_codigo_return(self, codigo: str, producto: Producto | None) -> None:
        self._buscar_por_codigo_retorno[codigo] = producto

    async def existe_codigo(self, codigo: str) -> bool:
        return await self.buscar_por_codigo(codigo) is not None

    async def siguiente_correlativo_interno(self, prefijo: str) -> int:
        maximo = 0
        for p in self._productos.values():
            if p.codigo.startswith(f"{prefijo}-"):
                sufijo = p.codigo.split("-", 1)[1]
                if sufijo.isdigit():
                    maximo = max(maximo, int(sufijo))
        return maximo + 1

    async def marcar_alerta_si_nueva(self, producto_id: int) -> bool:
        producto = self._productos.get(producto_id)
        if producto is None or producto.alerta_stock_notificada:
            return False
        producto.alerta_stock_notificada = True
        return True

    async def marcar_alertas_notificadas(self, producto_ids: list[int]) -> int:
        marcados = 0
        for pid in producto_ids:
            producto = self._productos.get(pid)
            if producto is not None:
                producto.alerta_stock_notificada = True
                marcados += 1
        return marcados

    async def buscar_por_id(self, producto_id: int) -> Producto | None:
        return self._productos.get(producto_id)

    async def crear(self, producto: Producto) -> Producto:
        self._contador += 1
        producto.id = self._contador
        self._productos[producto.id] = producto
        self.crear_call_count += 1
        self.crear_last_producto = producto
        return producto

    async def actualizar(self, producto_id: int, cambios: dict) -> Producto:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para actualizar — drift de Port")

    async def listar(self, busqueda: str | None = None) -> list[Producto]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar — drift de Port")

    async def listar_paginado(self, **_kwargs: Any) -> tuple[list[Producto], int]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_paginado — drift de Port")

    async def find_bajo_minimo(self, **_kwargs: Any) -> list[Producto]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para find_bajo_minimo — drift de Port")

    async def find_by_id_for_update(self, producto_id: int) -> Producto | None:
        return self._productos.get(producto_id)

    async def actualizar_general(
        self, producto_id: int, cambios: dict, usuario_id: int, usuario_nombre: str
    ) -> Producto:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para actualizar_general — drift de Port")

    async def actualizar_precio(
        self,
        producto_id: int,
        precio_venta: Decimal | None,
        precio_compra_actual: Decimal | None,
        usuario_id: int,
        usuario_nombre: str,
    ) -> tuple[Producto, list]:
        if self.actualizar_precio_return_value is None:
            producto = self._productos.get(producto_id)
            return (producto, [])  # sin cambios por default
        return self.actualizar_precio_return_value

    async def incrementar_stock_atomic(
        self, producto_id: int, delta: int
    ) -> tuple[bool, int | None]:
        return self.incrementar_stock_atomic_return_value


# =============================================================================
# Categoría
# =============================================================================


class MockCategoriaRepository:
    """Mock del `CategoriaRepositoryPort` con estado en memoria."""

    def __init__(self) -> None:
        self._categorias: dict[int, Categoria] = {}
        self._contador = 0
        self.crear_call_count = 0

    async def find_by_id(self, categoria_id: int) -> Categoria | None:
        return self._categorias.get(categoria_id)

    def add_categoria(self, categoria: Categoria) -> Categoria:
        """Utilidad para tests: añade una categoría existente al mock."""
        self._contador += 1
        categoria.id = self._contador
        self._categorias[categoria.id] = categoria
        return categoria

    async def crear(self, categoria: Categoria) -> Categoria:
        self._contador += 1
        categoria.id = self._contador
        self._categorias[categoria.id] = categoria
        self.crear_call_count += 1
        return categoria

    async def actualizar(
        self,
        categoria_id: int,
        cambios: dict,
        usuario_id: int | None = None,
        usuario_nombre: str | None = None,
    ) -> Categoria:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para actualizar — drift de Port")

    async def find_by_nombre(self, nombre: str) -> Categoria | None:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para find_by_nombre — drift de Port")

    async def listar(self) -> list[Categoria]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar — drift de Port")


# =============================================================================
# Historial de precio
# =============================================================================


class MockHistorialPrecioRepository:
    """Mock del `HistorialPrecioRepositoryPort` con lista append-only."""

    def __init__(self) -> None:
        self._filas: list[HistorialPrecio] = []
        self._contador = 0
        self.append_call_count = 0

    async def append(self, historial: HistorialPrecio) -> HistorialPrecio:
        self._contador += 1
        historial.id = self._contador
        self._filas.append(historial)
        self.append_call_count += 1
        return historial

    async def listar_por_producto(
        self,
        producto_id: int,
        *,
        tipo: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[HistorialPrecio], int]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_por_producto — drift de Port")


# =============================================================================
# Solicitud de ingreso
# =============================================================================


class MockSolicitudIngresoRepository:
    """Mock del `SolicitudIngresoRepositoryPort` con estado en memoria."""

    def __init__(self) -> None:
        self._solicitudes: dict[int, SolicitudIngreso] = {}
        self._contador = 0
        self.crear_call_count = 0
        self.crear_last_solicitud: SolicitudIngreso | None = None

    async def crear(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        self._contador += 1
        solicitud.id = self._contador
        self._solicitudes[solicitud.id] = solicitud
        self.crear_call_count += 1
        self.crear_last_solicitud = solicitud
        return solicitud

    async def find_by_id(self, solicitud_id: int) -> SolicitudIngreso | None:
        return self._solicitudes.get(solicitud_id)

    async def find_by_id_for_update(self, solicitud_id: int) -> SolicitudIngreso | None:
        return self._solicitudes.get(solicitud_id)

    async def actualizar(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:  # pragma: no cover
        self._solicitudes[solicitud.id] = solicitud
        return solicitud

    async def actualizar_cabecera(self, solicitud_id: int, cambios: dict) -> SolicitudIngreso:
        s = self._solicitudes.get(solicitud_id)
        if s is None:
            return None  # type: ignore[return-value]
        for k, v in cambios.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s

    async def listar_paginado(self, **_kwargs: Any) -> tuple[list[SolicitudIngreso], int]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_paginado — drift de Port")

    async def listar_por_solicitante(
        self, usuario_id: int, **_kwargs: Any
    ) -> tuple[list[SolicitudIngreso], int]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_por_solicitante — drift de Port")


# =============================================================================
# Detalle de solicitud
# =============================================================================


class MockDetalleSolicitudRepository:
    """Mock del `DetalleSolicitudRepositoryPort` con lista append-only."""

    def __init__(self) -> None:
        self._detalles: list[DetalleSolicitud] = []
        self._contador = 0
        self.crear_bulk_call_count = 0
        self.eliminar_por_solicitud_call_count = 0
        self.crear_bulk_last_lista: list[DetalleSolicitud] | None = None

    async def crear_bulk(self, detalles: list[DetalleSolicitud]) -> list[DetalleSolicitud]:
        for d in detalles:
            self._contador += 1
            d.id = self._contador
            self._detalles.append(d)
        self.crear_bulk_call_count += 1
        self.crear_bulk_last_lista = detalles
        return detalles

    async def listar_por_solicitud(self, solicitud_id: int) -> list[DetalleSolicitud]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_por_solicitud — drift de Port")

    async def eliminar_por_solicitud(self, solicitud_id: int) -> None:
        self.eliminar_por_solicitud_call_count += 1
        self._detalles = [d for d in self._detalles if d.solicitud_id != solicitud_id]


# =============================================================================
# Proveedor
# =============================================================================


class MockProveedorRepository:
    """Mock del `ProveedorRepositoryPort` con estado en memoria."""

    def __init__(self) -> None:
        self._proveedores: dict[int, Proveedor] = {}
        self._contador = 0
        self.incrementar_deuda_atomic_return_value: bool = True
        self.incrementar_deuda_atomic_call_count = 0
        self.incrementar_deuda_atomic_last_delta: Decimal | None = None

    def add_proveedor(self, proveedor: Proveedor) -> Proveedor:
        self._contador += 1
        proveedor.id = self._contador
        self._proveedores[proveedor.id] = proveedor
        return proveedor

    async def crear(self, proveedor: Proveedor) -> Proveedor:
        self._contador += 1
        proveedor.id = self._contador
        self._proveedores[proveedor.id] = proveedor
        return proveedor

    async def find_by_id(self, proveedor_id: int) -> Proveedor | None:
        return self._proveedores.get(proveedor_id)

    async def find_by_id_for_update(self, proveedor_id: int) -> Proveedor | None:
        return self._proveedores.get(proveedor_id)

    async def actualizar(self, proveedor: Proveedor) -> Proveedor:  # pragma: no cover
        self._proveedores[proveedor.id] = proveedor
        return proveedor

    async def listar_paginado(self, **_kwargs: Any) -> tuple[list[Proveedor], int]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_paginado — drift de Port")

    async def find_by_ruc(self, ruc: str) -> Proveedor | None:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para find_by_ruc — drift de Port")

    async def incrementar_deuda_atomic(self, proveedor_id: int, delta: Decimal) -> bool:
        self.incrementar_deuda_atomic_call_count += 1
        self.incrementar_deuda_atomic_last_delta = Decimal(str(delta))
        return self.incrementar_deuda_atomic_return_value


# =============================================================================
# Pago proveedor
# =============================================================================


class MockPagoProveedorRepository:
    """Mock del `PagoProveedorRepositoryPort` con lista append-only."""

    def __init__(self) -> None:
        self._pagos: list[PagoProveedor] = []
        self._contador = 0
        self.crear_call_count = 0
        self.crear_last_pago: PagoProveedor | None = None

    async def crear(self, pago: PagoProveedor) -> PagoProveedor:
        self._contador += 1
        pago.id = self._contador
        self._pagos.append(pago)
        self.crear_call_count += 1
        self.crear_last_pago = pago
        return pago

    async def listar_por_proveedor(
        self,
        proveedor_id: int,
        *,
        tipo: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PagoProveedor], int]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_por_proveedor — drift de Port")

    async def sum_tipo(self, proveedor_id: int, tipo: str) -> Decimal:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para sum_tipo — drift de Port")


# =============================================================================
# Movimiento inventario
# =============================================================================


class MockMovimientoInventarioRepository:
    """Mock del `MovimientoInventarioRepositoryPort` con lista append-only."""

    def __init__(self) -> None:
        self._movimientos: list[MovimientoInventario] = []
        self._contador = 0
        self.append_call_count = 0
        self.append_last_movimiento: MovimientoInventario | None = None

    async def append(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        self._contador += 1
        movimiento.id = self._contador
        self._movimientos.append(movimiento)
        self.append_call_count += 1
        self.append_last_movimiento = movimiento
        return movimiento

    async def listar_paginado(self, **_kwargs: Any) -> tuple[list[MovimientoInventario], int]:  # pragma: no cover
        raise NotImplementedError("Mock no configurado para listar_paginado — drift de Port")


# =============================================================================
# Auditoría (cross-module, único AsyncMock permitido)
# =============================================================================


def make_auditoria_mock() -> AsyncMock:
    """Retorna un `AsyncMock` con `ejecutar = AsyncMock(return_value=None)`.

    Único `AsyncMock` permitido por CN-6: `RegistrarAuditoriaUseCase` es una
    dependencia cross-module del Módulo A sin estado relevante para estos
    tests. Cualquier cambio de firma hace fallar el test (señal correcta).
    """
    auditoria = AsyncMock()
    auditoria.ejecutar = AsyncMock(return_value=None)
    return auditoria
