"""Tests de regresión de las correcciones del Módulo B (revisión 2026-07-25).

Cada test corresponde a un bug concreto detectado revisando el flujo HU-B01..B14
y falla si el bug vuelve. Todos son unitarios (Mocks del Port, sin BD).
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.confirmar_merma_usecase import (
    ConfirmarMermaUseCase,
)
from app.modules.modulo_b_inventario.application.crear_producto_usecase import (
    CrearProductoUseCase,
)
from app.modules.modulo_b_inventario.application.editar_merma_usecase import (
    EditarMermaUseCase,
)
from app.modules.modulo_b_inventario.application.editar_proveedor_usecase import (
    EditarProveedorUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Merma, Producto
from app.modules.modulo_b_inventario.domain.value_objects import EstadoMerma, MotivoMerma
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    CambiarPrecioRequest,
    MermaUpdateRequest,
    PagoProveedorCreate,
    ProductoUpdate,
    ProveedorUpdate,
    SolicitudIngresoUpdateRequest,
)
from app.shared.kernel.exceptions import (
    NoEncontradoError,
    ProhibidoError,
    ValidacionError,
)

from ._mocks import (
    MockCategoriaRepository,
    MockHistorialPrecioRepository,
    MockMermaRepository,
    MockMovimientoInventarioRepository,
    MockProductoRepository,
    MockProveedorRepository,
    make_auditoria_mock,
)


def _merma_registrada(producto_id: int = 1, registrado_por: int = 7) -> Merma:
    return Merma(
        id=None,
        producto_id=producto_id,
        cantidad=2,
        motivo=MotivoMerma("rotura"),
        registrado_por=registrado_por,
        registrado_por_nombre="Cajero",
        estado=EstadoMerma("Registrada"),
    )


# =============================================================================
# HU-B12: confirmar merma
# =============================================================================


def test_confirmar_merma_setea_confirmado_en() -> None:
    """Sin `confirmado_en`, el UPDATE viola chk_mermas_estado_consistente (500)."""
    merma = _merma_registrada()
    merma.confirmar(usuario_id=1, nombre="Admin")
    assert merma.confirmado_en is not None
    assert str(merma.estado) == "Confirmada"


def test_cajero_no_confirma_su_propia_merma() -> None:
    """D-14: flujo de 2 pasos; quien registra no valida (salvo ADMIN)."""

    async def _run():
        mermas = MockMermaRepository()
        merma = mermas.add_merma(_merma_registrada(registrado_por=7))
        use_case = ConfirmarMermaUseCase(
            mermas,
            MockProductoRepository(),
            MockMovimientoInventarioRepository(),
            make_auditoria_mock(),
        )
        with pytest.raises(ProhibidoError):
            await use_case.ejecutar(
                merma_id=merma.id,
                usuario_id=7,
                usuario_nombre="Cajero",
                es_admin=False,
            )

    asyncio.run(_run())


# =============================================================================
# HU-B03: códigos internos y de barras
# =============================================================================


def _use_case_producto(productos: MockProductoRepository) -> CrearProductoUseCase:
    return CrearProductoUseCase(
        producto_repo=productos,
        categoria_repo=MockCategoriaRepository(),
        historial_repo=MockHistorialPrecioRepository(),
        auditoria=make_auditoria_mock(),
    )


def test_barcode_con_formato_de_codigo_interno_se_rechaza() -> None:
    """El guard estaba dentro de un try/except que se tragaba su propio raise."""

    async def _run():
        productos = MockProductoRepository()
        with pytest.raises(ValidacionError) as exc:
            await _use_case_producto(productos).ejecutar(
                codigo="PAP-001",
                nombre="Colisión",
                categoria_id=None,
                precio_venta=Decimal("10"),
                precio_compra_actual=Decimal("0"),
                es_codigo_interno=False,
                usuario_id=1,
                usuario_nombre="Admin",
            )
        assert "código interno" in str(exc.value)
        assert productos.crear_call_count == 0

    asyncio.run(_run())


def test_codigo_interno_es_correlativo_y_no_timestamp() -> None:
    """HU-B03 pide PAP-001, PAP-002...; antes salía PAP-{HHMMSS} y PAP-...X."""

    async def _run():
        productos = MockProductoRepository()
        use_case = _use_case_producto(productos)
        codigos = []
        for i in range(3):
            await use_case.ejecutar(
                codigo=None,
                nombre=f"Interno {i}",
                categoria_id=None,
                precio_venta=Decimal("10"),
                precio_compra_actual=Decimal("0"),
                es_codigo_interno=True,
                usuario_id=1,
                usuario_nombre="Admin",
            )
            codigos.append(productos.crear_last_producto.codigo)
        assert codigos == ["PAP-001", "PAP-002", "PAP-003"]

    asyncio.run(_run())


def test_codigo_de_producto_borrado_da_conflicto_no_500() -> None:
    """El UNIQUE de productos.codigo es global: hay que mirar también borrados."""

    async def _run():
        productos = MockProductoRepository()
        borrado = Producto(
            id=50,
            codigo="BC-BORRADO",
            nombre="Viejo",
            categoria_id=None,
            precio=Decimal("1"),
        )
        from datetime import datetime, timezone

        borrado.deleted_at = datetime.now(timezone.utc)
        productos.set_buscar_por_codigo_return("BC-BORRADO", borrado)
        from app.shared.kernel.exceptions import ConflictoError

        with pytest.raises(ConflictoError):
            await _use_case_producto(productos).ejecutar(
                codigo="BC-BORRADO",
                nombre="Nuevo",
                categoria_id=None,
                precio_venta=Decimal("10"),
                precio_compra_actual=Decimal("0"),
                usuario_id=1,
                usuario_nombre="Admin",
            )

    asyncio.run(_run())


# =============================================================================
# HU-B13: alerta de reposición
# =============================================================================


def test_producto_sin_stock_minimo_no_requiere_reposicion() -> None:
    """stock_minimo = 0 significa 'sin umbral', no 'alertar siempre'."""
    p = Producto(
        id=1, codigo="X", nombre="X", categoria_id=None, precio=Decimal("1"),
        stock=0, stock_minimo=0,
    )
    assert p.requiere_reposicion() is False
    p.stock_minimo = 3
    assert p.requiere_reposicion() is True


# =============================================================================
# FKs en las ediciones
# =============================================================================


def test_editar_merma_valida_producto_inexistente() -> None:
    """Antes llegaba al UPDATE y Postgres devolvía violación de FK (500)."""

    async def _run():
        mermas = MockMermaRepository()
        merma = mermas.add_merma(_merma_registrada())
        use_case = EditarMermaUseCase(
            mermas,
            make_auditoria_mock(),
            producto_repo=MockProductoRepository(),  # vacío: nada existe
            proveedor_repo=MockProveedorRepository(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                merma_id=merma.id,
                editor_id=1,
                editor_nombre="Admin",
                es_admin=True,
                producto_id=999999,
            )
        assert exc.value.code == "PRODUCTO_NOT_FOUND"

    asyncio.run(_run())


# =============================================================================
# HU-B14: proveedores
# =============================================================================


def test_editar_proveedor_inexistente_es_404_y_no_pisa_datos() -> None:
    """Antes construía la entidad con "" y el UPDATE borraba la razón social."""

    async def _run():
        proveedores = MockProveedorRepository()
        use_case = EditarProveedorUseCase(proveedores, make_auditoria_mock())
        with pytest.raises(NoEncontradoError):
            await use_case.ejecutar(
                proveedor_id=999999,
                cambios={"telefono": "111"},
                usuario_id=1,
                usuario_nombre="Admin",
            )

    asyncio.run(_run())


# =============================================================================
# Contratos HTTP (validación de body)
# =============================================================================


def test_producto_update_rechaza_precio() -> None:
    """Antes Pydantic descartaba `precio` y el PATCH respondía 200 sin cambiarlo."""
    with pytest.raises(Exception):
        ProductoUpdate(nombre="X", precio=999)


def test_cambiar_precio_rechaza_venta_en_cero() -> None:
    with pytest.raises(Exception):
        CambiarPrecioRequest(precio_venta=0)
    assert CambiarPrecioRequest(precio_venta=1500).precio_venta == 1500


def test_proveedor_update_valida_email() -> None:
    with pytest.raises(Exception):
        ProveedorUpdate(email="no-es-un-email")
    assert ProveedorUpdate(email="a@b.com").email == "a@b.com"


def test_pago_proveedor_create_no_acepta_campos_extra() -> None:
    with pytest.raises(Exception):
        PagoProveedorCreate(monto=10, fecha="2026-07-25", inventado=True)


def test_patch_parcial_no_pisa_los_campos_ausentes() -> None:
    """PATCH {"cantidad": 2} no debe interpretarse como 'motivo = None'.

    Antes el router mandaba `motivo=None` al use case y la merma respondía 422
    INVALID_MOTIVO; en ingresos, un PATCH de solo `lineas` borraba el proveedor.
    """
    merma = MermaUpdateRequest(cantidad=2)
    assert merma.valor("cantidad") == 2
    assert merma.valor("motivo") is ...
    assert merma.valor("observacion") is ...

    ingreso = SolicitudIngresoUpdateRequest(
        lineas=[{"producto_id": 1, "cantidad": 2, "precio_unitario": 3}]
    )
    assert ingreso.valor("proveedor_id") is ...
    assert ingreso.valor("motivo") is ...

    # Enviar el campo explícitamente en null SÍ es un cambio (limpiar el valor).
    assert MermaUpdateRequest(observacion=None).valor("observacion") is None

    with pytest.raises(Exception):
        MermaUpdateRequest()  # body vacío
