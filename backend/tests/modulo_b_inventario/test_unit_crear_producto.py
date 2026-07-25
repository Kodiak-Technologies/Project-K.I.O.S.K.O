"""Unit tests for `CrearProductoUseCase` (HU-B01, HU-B03, REQ-04, REQ-08).

RED: cada aserción fallaría si el use case omitiera la validación, el append al
historial_precios (venta + compra) o la auditoría.

GREEN: las 6 aserciones pasan con Mocks que cumplen el Port.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.crear_producto_usecase import (
    CrearProductoUseCase,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)

from ._mocks import (
    MockCategoriaRepository,
    MockHistorialPrecioRepository,
    MockProductoRepository,
    make_auditoria_mock,
)


def _build():
    """Helper que construye el use case con Mocks frescos para cada test."""
    return (
        CrearProductoUseCase(
            producto_repo=MockProductoRepository(),
            categoria_repo=MockCategoriaRepository(),
            historial_repo=MockHistorialPrecioRepository(),
            auditoria=make_auditoria_mock(),
        ),
    )


def test_crear_producto_con_codigo_barras_happy() -> None:
    """Camino feliz: barcode manual, no interno. Crea producto, append 2 al historial,
    llama auditoría con accion='producto_creado' y retorna el producto con id no nulo."""

    async def _run():
        productos, categorias, historial, auditoria = (
            MockProductoRepository(),
            MockCategoriaRepository(),
            MockHistorialPrecioRepository(),
            make_auditoria_mock(),
        )
        use_case = CrearProductoUseCase(
            producto_repo=productos,
            categoria_repo=categorias,
            historial_repo=historial,
            auditoria=auditoria,
        )
        creado = await use_case.ejecutar(
            codigo="BC-12345",
            nombre="Gaseosa",
            categoria_id=None,
            precio_venta=Decimal("10.00"),
            precio_compra_actual=Decimal("5.00"),
            es_codigo_interno=False,
            usuario_id=1,
            usuario_nombre="Admin",
        )
        # 1) producto.crear se llamó una vez
        assert productos.crear_call_count == 1
        assert productos.crear_last_producto is not None
        assert productos.crear_last_producto.codigo == "BC-12345"
        assert productos.crear_last_producto.activo is True
        assert productos.crear_last_producto.es_codigo_interno is False
        # 2) historial.append se llamó DOS veces (venta + compra)
        assert historial.append_call_count == 2
        # 3) auditoría con accion correcta
        assert auditoria.ejecutar.await_count == 1
        call_kwargs = auditoria.ejecutar.await_args.kwargs
        assert call_kwargs["accion"] == "producto_creado"
        assert call_kwargs["entidad"] == "productos"
        # 4) retorno tiene id no nulo
        assert creado.id is not None

    asyncio.run(_run())


def test_nombre_vacio_levanta_validacion_error() -> None:
    """Nombre vacío (o solo whitespace) levanta ValidacionError y NO persiste nada."""

    async def _run():
        productos = MockProductoRepository()
        categorias = MockCategoriaRepository()
        historial = MockHistorialPrecioRepository()
        auditoria = make_auditoria_mock()
        use_case = CrearProductoUseCase(
            producto_repo=productos,
            categoria_repo=categorias,
            historial_repo=historial,
            auditoria=auditoria,
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                codigo="BC-999",
                nombre="   ",
                categoria_id=None,
                precio_venta=Decimal("10.00"),
                precio_compra_actual=Decimal("5.00"),
                usuario_id=1,
                usuario_nombre="Admin",
            )
        assert "obligatorio" in str(exc.value).lower()
        # No se llamó crear ni historial ni auditoría
        assert productos.crear_call_count == 0
        assert historial.append_call_count == 0
        assert auditoria.ejecutar.await_count == 0

    asyncio.run(_run())


def test_precio_venta_cero_levanta_validacion_error() -> None:
    """precio_venta <= 0 levanta ValidacionError y no persiste nada."""

    async def _run():
        productos = MockProductoRepository()
        historial = MockHistorialPrecioRepository()
        auditoria = make_auditoria_mock()
        use_case = CrearProductoUseCase(
            producto_repo=productos,
            categoria_repo=MockCategoriaRepository(),
            historial_repo=historial,
            auditoria=auditoria,
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                codigo="BC-998",
                nombre="X",
                categoria_id=None,
                precio_venta=Decimal("0"),
                precio_compra_actual=Decimal("0"),
                usuario_id=1,
                usuario_nombre="Admin",
            )
        assert "mayor a 0" in str(exc.value)
        assert productos.crear_call_count == 0
        assert historial.append_call_count == 0
        assert auditoria.ejecutar.await_count == 0

    asyncio.run(_run())


def test_codigo_interno_autogenera_prefijo_pap() -> None:
    """es_codigo_interno=True sin codigo → autogenera con prefijo PAP-CORRELATIVO."""

    async def _run():
        productos = MockProductoRepository()
        use_case = CrearProductoUseCase(
            producto_repo=productos,
            categoria_repo=MockCategoriaRepository(),
            historial_repo=MockHistorialPrecioRepository(),
            auditoria=make_auditoria_mock(),
        )
        await use_case.ejecutar(
            codigo=None,
            nombre="Producto Interno",
            categoria_id=None,
            precio_venta=Decimal("7.00"),
            precio_compra_actual=Decimal("3.50"),
            es_codigo_interno=True,
            usuario_id=1,
            usuario_nombre="Admin",
        )
        codigo_generado = productos.crear_last_producto.codigo
        assert codigo_generado.startswith("PAP-")
        # Valida patrón ^[A-Z]{2,5}-\d{3,6}$
        import re

        assert re.match(r"^[A-Z]{2,5}-\d{3,6}$", codigo_generado), codigo_generado

    asyncio.run(_run())


def test_codigo_duplicado_levanta_conflicto_error() -> None:
    """MockProductoRepository.buscar_por_codigo retorna producto existente → ConflictoError."""

    async def _run():
        productos = MockProductoRepository()
        from app.modules.modulo_b_inventario.domain.entities import Producto

        existente = Producto(
            id=99,
            codigo="BC-DUP",
            nombre="Otro",
            categoria_id=None,
            precio=Decimal("1.00"),
        )
        productos.set_buscar_por_codigo_return("BC-DUP", existente)
        use_case = CrearProductoUseCase(
            producto_repo=productos,
            categoria_repo=MockCategoriaRepository(),
            historial_repo=MockHistorialPrecioRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ConflictoError) as exc:
            await use_case.ejecutar(
                codigo="BC-DUP",
                nombre="Nuevo",
                categoria_id=None,
                precio_venta=Decimal("10.00"),
                precio_compra_actual=Decimal("0"),
                usuario_id=1,
                usuario_nombre="Admin",
            )
        assert "Ya existe" in str(exc.value)
        assert productos.crear_call_count == 0

    asyncio.run(_run())


def test_categoria_inexistente_levanta_no_encontrado_error() -> None:
    """MockCategoriaRepository.find_by_id retorna None → NoEncontradoError."""

    async def _run():
        productos = MockProductoRepository()
        categorias = MockCategoriaRepository()  # sin categorías
        use_case = CrearProductoUseCase(
            producto_repo=productos,
            categoria_repo=categorias,
            historial_repo=MockHistorialPrecioRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(NoEncontradoError) as exc:
            await use_case.ejecutar(
                codigo="BC-777",
                nombre="X",
                categoria_id=999,
                precio_venta=Decimal("10.00"),
                precio_compra_actual=Decimal("0"),
                usuario_id=1,
                usuario_nombre="Admin",
            )
        assert "Categor" in str(exc.value)
        assert productos.crear_call_count == 0

    asyncio.run(_run())
