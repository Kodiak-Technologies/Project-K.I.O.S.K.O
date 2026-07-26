"""Unit tests for `RegistrarCompraCreditoUseCase` (HU-B14, REQ-CC).

RED: cada aserción fallaría si el use case omitiera validar monto/proveedor/solicitud,
o si no insertara el PagoProveedor con tipo='compra_credito' e incrementara la deuda.

GREEN: las 5 aserciones pasan con Mocks que cumplen el Port.
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.registrar_compra_credito_usecase import (
    RegistrarCompraCreditoUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Proveedor
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError

from ._mocks import (
    MockPagoProveedorRepository,
    MockProveedorRepository,
    MockSolicitudIngresoRepository,
    make_auditoria_mock,
)


def test_compra_credito_con_monto_y_proveedor_validos_happy() -> None:
    """Camino feliz: inserta PagoProveedor tipo='compra_credito' e incrementa deuda."""

    async def _run():
        proveedores = MockProveedorRepository()
        pagos = MockPagoProveedorRepository()
        solicitudes = MockSolicitudIngresoRepository()
        auditoria = make_auditoria_mock()
        proveedores.add_proveedor(
            Proveedor(
                id=None,
                razon_social="Prov",
                creado_por=1,
                creado_por_nombre="A",
            )
        )
        use_case = RegistrarCompraCreditoUseCase(
            proveedor_repo=proveedores,
            pago_repo=pagos,
            solicitud_repo=solicitudes,
            auditoria=auditoria,
        )
        prov_id = next(iter(proveedores._proveedores.keys()))
        pago = await use_case.ejecutar(
            proveedor_id=prov_id,
            monto=Decimal("100.00"),
            fecha=date(2026, 7, 25),
            concepto="Compra de prueba",
            solicitud_ingreso_id=None,
            usuario_id=1,
            usuario_nombre="Admin",
        )
        assert pagos.crear_call_count == 1
        assert str(pago.tipo) == "compra_credito"
        assert pago.monto == Decimal("100.00")
        assert proveedores.incrementar_deuda_atomic_call_count == 1
        assert proveedores.incrementar_deuda_atomic_last_delta == Decimal("100.00")
        assert auditoria.ejecutar.await_count == 1
        assert auditoria.ejecutar.await_args.kwargs["accion"] == "compra_credito"

    asyncio.run(_run())


def test_monto_cero_levanta_validacion_error() -> None:
    """monto=0 levanta ValidacionError y NO se llama find_by_id_for_update."""

    async def _run():
        proveedores = MockProveedorRepository()
        use_case = RegistrarCompraCreditoUseCase(
            proveedor_repo=proveedores,
            pago_repo=MockPagoProveedorRepository(),
            solicitud_repo=MockSolicitudIngresoRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=1,
                monto=Decimal("0"),
                fecha=date(2026, 7, 25),
                concepto=None,
                solicitud_ingreso_id=None,
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "mayor a 0" in str(exc.value)

    asyncio.run(_run())


def test_proveedor_inexistente_levanta_no_encontrado_error() -> None:
    """MockProveedorRepository.find_by_id_for_update=None → NoEncontradoError."""

    async def _run():
        proveedores = MockProveedorRepository()
        pagos = MockPagoProveedorRepository()
        use_case = RegistrarCompraCreditoUseCase(
            proveedor_repo=proveedores,
            pago_repo=pagos,
            solicitud_repo=MockSolicitudIngresoRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(NoEncontradoError) as exc:
            await use_case.ejecutar(
                proveedor_id=999,
                monto=Decimal("100.00"),
                fecha=date(2026, 7, 25),
                concepto=None,
                solicitud_ingreso_id=None,
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "proveedor" in str(exc.value).lower()
        assert pagos.crear_call_count == 0

    asyncio.run(_run())


def test_solicitud_ingreso_inexistente_levanta_no_encontrado_error() -> None:
    """solicitud_ingreso_id=999 con MockSolicitudIngresoRepository.find_by_id=None → NoEncontradoError."""

    async def _run():
        proveedores = MockProveedorRepository()
        proveedores.add_proveedor(
            Proveedor(id=None, razon_social="P", creado_por=1, creado_por_nombre="A")
        )
        pagos = MockPagoProveedorRepository()
        use_case = RegistrarCompraCreditoUseCase(
            proveedor_repo=proveedores,
            pago_repo=pagos,
            solicitud_repo=MockSolicitudIngresoRepository(),
            auditoria=make_auditoria_mock(),
        )
        prov_id = next(iter(proveedores._proveedores.keys()))
        with pytest.raises(NoEncontradoError) as exc:
            await use_case.ejecutar(
                proveedor_id=prov_id,
                monto=Decimal("100.00"),
                fecha=date(2026, 7, 25),
                concepto=None,
                solicitud_ingreso_id=999,
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "solicitud" in str(exc.value).lower()
        assert pagos.crear_call_count == 0

    asyncio.run(_run())


def test_fecha_formato_invalido_levanta_validacion_error() -> None:
    """fecha='25-07-2026' (formato DD-MM-YYYY) levanta ValidacionError con mensaje YYYY-MM-DD."""

    async def _run():
        proveedores = MockProveedorRepository()
        proveedores.add_proveedor(
            Proveedor(id=None, razon_social="P", creado_por=1, creado_por_nombre="A")
        )
        use_case = RegistrarCompraCreditoUseCase(
            proveedor_repo=proveedores,
            pago_repo=MockPagoProveedorRepository(),
            solicitud_repo=MockSolicitudIngresoRepository(),
            auditoria=make_auditoria_mock(),
        )
        prov_id = next(iter(proveedores._proveedores.keys()))
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=prov_id,
                monto=Decimal("100.00"),
                fecha="25-07-2026",
                concepto=None,
                solicitud_ingreso_id=None,
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "YYYY-MM-DD" in str(exc.value)

    asyncio.run(_run())
