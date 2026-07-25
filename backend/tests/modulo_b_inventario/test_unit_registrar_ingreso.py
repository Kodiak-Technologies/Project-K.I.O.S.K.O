"""Unit tests for `RegistrarIngresoUseCase` (HU-B05/06, REQ-ING).

RED: cada aserción fallaría si el use case omitiera validar foto, líneas,
existencia de productos, o si no creara la solicitud + detalles y la auditoría.

GREEN: las 7 aserciones pasan con Mocks que cumplen el Port.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.registrar_ingreso_usecase import (
    LineaSolicitudDTO,
    RegistrarIngresoUseCase,
)
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError

from ._mocks import (
    MockDetalleSolicitudRepository,
    MockProductoRepository,
    MockProveedorRepository,
    MockSolicitudIngresoRepository,
    make_auditoria_mock,
)


def test_ingreso_con_foto_y_lineas_validas_happy() -> None:
    """Camino feliz: crea solicitud Pendiente, inserta bulk de detalles, audita."""

    async def _run():
        solicitudes = MockSolicitudIngresoRepository()
        detalles = MockDetalleSolicitudRepository()
        productos = MockProductoRepository()
        proveedores = MockProveedorRepository()
        auditoria = make_auditoria_mock()
        # Producto existente en el repo mock
        from app.modules.modulo_b_inventario.domain.entities import Producto

        prod = Producto(
            id=10,
            codigo="P-OK",
            nombre="Prod",
            categoria_id=None,
            precio=Decimal("1.00"),
        )
        productos._productos[10] = prod
        # Proveedor existente (id asignado por el mock al agregar)
        from app.modules.modulo_b_inventario.domain.entities import Proveedor

        prov = proveedores.add_proveedor(
            Proveedor(
                id=None,
                razon_social="Prov",
                creado_por=1,
                creado_por_nombre="A",
            )
        )
        use_case = RegistrarIngresoUseCase(
            solicitud_repo=solicitudes,
            detalle_repo=detalles,
            producto_repo=productos,
            proveedor_repo=proveedores,
            auditoria=auditoria,
        )
        await use_case.ejecutar(
            proveedor_id=prov.id,
            foto_boleta_url="https://x.test/boleta.jpg",
            lineas=[LineaSolicitudDTO(producto_id=10, cantidad=5, precio_compra_unitario=Decimal("10.00"))],
            usuario_id=1,
            usuario_nombre="Cajero",
        )
        assert solicitudes.crear_call_count == 1
        assert solicitudes.crear_last_solicitud.estado.valor == "Pendiente"
        assert solicitudes.crear_last_solicitud.solicitado_por == 1
        assert detalles.crear_bulk_call_count == 1
        assert len(detalles.crear_bulk_last_lista) == 1
        assert auditoria.ejecutar.await_count == 1
        kwargs = auditoria.ejecutar.await_args.kwargs
        assert kwargs["accion"] == "ingreso_solicitado"
        assert kwargs["valor_nuevo"]["cantidad_productos"] == 1

    asyncio.run(_run())


def test_foto_vacia_levanta_validacion_error() -> None:
    """foto_boleta_url='' levanta ValidacionError y NO llama solicitudes.crear."""

    async def _run():
        solicitudes = MockSolicitudIngresoRepository()
        detalles = MockDetalleSolicitudRepository()
        productos = MockProductoRepository()
        proveedores = MockProveedorRepository()
        use_case = RegistrarIngresoUseCase(
            solicitud_repo=solicitudes,
            detalle_repo=detalles,
            producto_repo=productos,
            proveedor_repo=proveedores,
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=None,
                foto_boleta_url="",
                lineas=[LineaSolicitudDTO(producto_id=1, cantidad=1, precio_compra_unitario=Decimal("1.00"))],
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "boleta" in str(exc.value).lower()
        assert solicitudes.crear_call_count == 0

    asyncio.run(_run())


def test_lineas_vacias_levanta_validacion_error() -> None:
    """lineas=[] levanta ValidacionError."""

    async def _run():
        solicitudes = MockSolicitudIngresoRepository()
        use_case = RegistrarIngresoUseCase(
            solicitud_repo=solicitudes,
            detalle_repo=MockDetalleSolicitudRepository(),
            producto_repo=MockProductoRepository(),
            proveedor_repo=MockProveedorRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=None,
                foto_boleta_url="https://x.test/b.jpg",
                lineas=[],
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "al menos una" in str(exc.value).lower()
        assert solicitudes.crear_call_count == 0

    asyncio.run(_run())


def test_linea_cantidad_cero_levanta_validacion_error() -> None:
    """Línea con cantidad=0 levanta ValidacionError mencionando 'línea 1' y 'cantidad'."""

    async def _run():
        use_case = RegistrarIngresoUseCase(
            solicitud_repo=MockSolicitudIngresoRepository(),
            detalle_repo=MockDetalleSolicitudRepository(),
            producto_repo=MockProductoRepository(),
            proveedor_repo=MockProveedorRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=None,
                foto_boleta_url="https://x.test/b.jpg",
                lineas=[LineaSolicitudDTO(producto_id=1, cantidad=0, precio_compra_unitario=Decimal("1.00"))],
                usuario_id=1,
                usuario_nombre="X",
            )
        msg = str(exc.value).lower()
        assert "línea 1" in msg and "cantidad" in msg

    asyncio.run(_run())


def test_linea_precio_negativo_levanta_validacion_error() -> None:
    """Línea con precio_compra_unitario<0 levanta ValidacionError mencionando 'línea 1'."""

    async def _run():
        use_case = RegistrarIngresoUseCase(
            solicitud_repo=MockSolicitudIngresoRepository(),
            detalle_repo=MockDetalleSolicitudRepository(),
            producto_repo=MockProductoRepository(),
            proveedor_repo=MockProveedorRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=None,
                foto_boleta_url="https://x.test/b.jpg",
                lineas=[LineaSolicitudDTO(producto_id=1, cantidad=1, precio_compra_unitario=Decimal("-1.00"))],
                usuario_id=1,
                usuario_nombre="X",
            )
        msg = str(exc.value).lower()
        assert "línea 1" in msg and "precio" in msg

    asyncio.run(_run())


def test_producto_inexistente_en_linea_levanta_no_encontrado_error() -> None:
    """producto_id=999 con MockProductoRepository.buscar_por_id=None → NoEncontradoError."""

    async def _run():
        use_case = RegistrarIngresoUseCase(
            solicitud_repo=MockSolicitudIngresoRepository(),
            detalle_repo=MockDetalleSolicitudRepository(),
            producto_repo=MockProductoRepository(),  # vacío
            proveedor_repo=MockProveedorRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(NoEncontradoError) as exc:
            await use_case.ejecutar(
                proveedor_id=None,
                foto_boleta_url="https://x.test/b.jpg",
                lineas=[LineaSolicitudDTO(producto_id=999, cantidad=1, precio_compra_unitario=Decimal("1.00"))],
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "línea 1" in str(exc.value).lower()
        assert "producto" in str(exc.value).lower()

    asyncio.run(_run())


def test_proveedor_none_omite_validacion() -> None:
    """proveedor_id=None omite la validación y la solicitud se crea con proveedor_id=None."""

    async def _run():
        solicitudes = MockSolicitudIngresoRepository()
        productos = MockProductoRepository()
        from app.modules.modulo_b_inventario.domain.entities import Producto

        productos._productos[10] = Producto(
            id=10, codigo="P-OK", nombre="P", categoria_id=None, precio=Decimal("1.00")
        )
        proveedores = MockProveedorRepository()
        use_case = RegistrarIngresoUseCase(
            solicitud_repo=solicitudes,
            detalle_repo=MockDetalleSolicitudRepository(),
            producto_repo=productos,
            proveedor_repo=proveedores,
            auditoria=make_auditoria_mock(),
        )
        await use_case.ejecutar(
            proveedor_id=None,
            foto_boleta_url="https://x.test/b.jpg",
            lineas=[LineaSolicitudDTO(producto_id=10, cantidad=1, precio_compra_unitario=Decimal("1.00"))],
            usuario_id=1,
            usuario_nombre="X",
        )
        # No se llama proveedores.find_by_id (no hay cómo, el mock no lo trackea,
        # pero el resultado es que la solicitud se crea con proveedor_id=None).
        assert solicitudes.crear_call_count == 1
        assert solicitudes.crear_last_solicitud.proveedor_id is None

    asyncio.run(_run())
