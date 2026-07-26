"""Unit tests for `CambiarPrecioUseCase` (cuerpo completo, HU-B11, REQ-11).

Sufijo `_full` para no chocar con el `test_unit_cambiar_precio.py` existente
que prueba la capa de adapter.

RED: cada aserción fallaría si el use case omitiera validar precios negativos,
si auditara sin cambio real, o si el repo no devolviera la tupla correcta.

GREEN: las 4 aserciones pasan con Mocks que cumplen el Port.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.cambiar_precio_usecase import (
    CambiarPrecioUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    HistorialPrecio,
    Producto,
)
from app.modules.modulo_b_inventario.domain.value_objects import TipoPrecio
from app.shared.kernel.exceptions import ValidacionError

from ._mocks import (
    MockHistorialPrecioRepository,
    MockProductoRepository,
    make_auditoria_mock,
)


def test_cambio_real_precio_venta_happy() -> None:
    """Cambio real de precio_venta → auditoría con accion='cambiar_precio' y filas_historial poblado."""

    async def _run():
        productos = MockProductoRepository()
        historial = MockHistorialPrecioRepository()
        auditoria = make_auditoria_mock()
        producto_actualizado = Producto(
            id=1,
            codigo="P-1",
            nombre="P",
            categoria_id=None,
            precio=Decimal("15.00"),
            precio_compra_actual=Decimal("5.00"),
        )
        fila_hist = HistorialPrecio(
            id=10,
            producto_id=1,
            precio_nuevo=Decimal("15.00"),
            tipo_precio=TipoPrecio("venta"),
            modificado_por=1,
            modificado_por_nombre="A",
            precio_anterior=Decimal("10.00"),
        )
        productos.actualizar_precio_return_value = (producto_actualizado, [fila_hist])
        use_case = CambiarPrecioUseCase(
            producto_repo=productos,
            historial_repo=historial,
            auditoria=auditoria,
        )
        prod_ret, hubo_cambio, filas = await use_case.ejecutar(
            producto_id=1,
            precio_venta=Decimal("15.00"),
            precio_compra_actual=None,
            usuario_id=1,
            usuario_nombre="Admin",
        )
        assert hubo_cambio is True
        assert len(filas) == 1
        assert auditoria.ejecutar.await_count == 1
        kwargs = auditoria.ejecutar.await_args.kwargs
        assert kwargs["accion"] == "cambiar_precio"
        assert kwargs["valor_nuevo"]["filas_historial"][0]["tipo"] == "venta"
        assert prod_ret.id == 1

    asyncio.run(_run())


def test_precio_venta_negativo_levanta_validacion_error() -> None:
    """precio_venta <= 0 levanta ValidacionError (igual que el alta) y NO persiste."""

    async def _run():
        productos = MockProductoRepository()
        auditoria = make_auditoria_mock()
        use_case = CambiarPrecioUseCase(
            producto_repo=productos,
            historial_repo=MockHistorialPrecioRepository(),
            auditoria=auditoria,
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                producto_id=1,
                precio_venta=Decimal("-1.00"),
                precio_compra_actual=None,
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "mayor a 0" in str(exc.value)
        assert auditoria.ejecutar.await_count == 0

    asyncio.run(_run())


def test_precio_compra_actual_negativo_levanta_validacion_error() -> None:
    """precio_compra_actual<0 levanta ValidacionError."""

    async def _run():
        use_case = CambiarPrecioUseCase(
            producto_repo=MockProductoRepository(),
            historial_repo=MockHistorialPrecioRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                producto_id=1,
                precio_venta=None,
                precio_compra_actual=Decimal("-1.00"),
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "precio_compra_actual" in str(exc.value)

    asyncio.run(_run())


def test_sin_cambio_real_no_registra_auditoria() -> None:
    """actualizar_precio retorna (producto, []) → NO auditoría, retorno (producto, False, [])."""

    async def _run():
        productos = MockProductoRepository()
        producto_sin_cambios = Producto(
            id=1,
            codigo="P-1",
            nombre="P",
            categoria_id=None,
            precio=Decimal("10.00"),
        )
        productos.actualizar_precio_return_value = (producto_sin_cambios, [])
        auditoria = make_auditoria_mock()
        use_case = CambiarPrecioUseCase(
            producto_repo=productos,
            historial_repo=MockHistorialPrecioRepository(),
            auditoria=auditoria,
        )
        prod_ret, hubo_cambio, filas = await use_case.ejecutar(
            producto_id=1,
            precio_venta=Decimal("10.00"),
            precio_compra_actual=None,
            usuario_id=1,
            usuario_nombre="X",
        )
        assert hubo_cambio is False
        assert filas == []
        assert auditoria.ejecutar.await_count == 0
        assert prod_ret.id == 1

    asyncio.run(_run())
