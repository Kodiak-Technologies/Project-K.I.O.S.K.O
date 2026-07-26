"""Unit tests for `RegistrarPagoProveedorUseCase` (HU-B14, REQ-PAG).

RED: cada aserción fallaría si el use case omitiera validar monto>0,
monto<=deuda_actual, existencia de proveedor, o si no insertara el PagoProveedor
tipo='pago' y decrementara la deuda.

GREEN: las 4 aserciones pasan con Mocks que cumplen el Port.
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.registrar_pago_proveedor_usecase import (
    RegistrarPagoProveedorUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Proveedor
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError

from ._mocks import (
    MockPagoProveedorRepository,
    MockProveedorRepository,
    make_auditoria_mock,
)


def test_pago_con_monto_menor_a_deuda_happy() -> None:
    """Pago menor a deuda_actual → crea PagoProveedor tipo='pago' e incrementa_deuda_atomic(-100)."""

    async def _run():
        proveedores = MockProveedorRepository()
        pagos = MockPagoProveedorRepository()
        auditoria = make_auditoria_mock()
        proveedores.add_proveedor(
            Proveedor(
                id=None,
                razon_social="P",
                creado_por=1,
                creado_por_nombre="A",
                deuda_actual=Decimal("200.00"),
            )
        )
        use_case = RegistrarPagoProveedorUseCase(
            proveedor_repo=proveedores,
            pago_repo=pagos,
            auditoria=auditoria,
        )
        prov_id = next(iter(proveedores._proveedores.keys()))
        pago = await use_case.ejecutar(
            proveedor_id=prov_id,
            monto=Decimal("100.00"),
            fecha=date(2026, 7, 25),
            concepto="Pago parcial",
            usuario_id=1,
            usuario_nombre="Admin",
        )
        assert pagos.crear_call_count == 1
        assert str(pago.tipo) == "pago"
        assert pago.monto == Decimal("100.00")
        assert proveedores.incrementar_deuda_atomic_call_count == 1
        assert proveedores.incrementar_deuda_atomic_last_delta == Decimal("-100.00")
        assert auditoria.ejecutar.await_count == 1
        assert auditoria.ejecutar.await_args.kwargs["accion"] == "pago_proveedor"

    asyncio.run(_run())


def test_monto_cero_levanta_validacion_error() -> None:
    """monto=0 levanta ValidacionError."""

    async def _run():
        use_case = RegistrarPagoProveedorUseCase(
            proveedor_repo=MockProveedorRepository(),
            pago_repo=MockPagoProveedorRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=1,
                monto=Decimal("0"),
                fecha=date(2026, 7, 25),
                concepto=None,
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
        use_case = RegistrarPagoProveedorUseCase(
            proveedor_repo=proveedores,
            pago_repo=pagos,
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(NoEncontradoError) as exc:
            await use_case.ejecutar(
                proveedor_id=999,
                monto=Decimal("50.00"),
                fecha=date(2026, 7, 25),
                concepto=None,
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "proveedor" in str(exc.value).lower()
        assert pagos.crear_call_count == 0

    asyncio.run(_run())


def test_monto_mayor_a_deuda_levanta_validacion_error() -> None:
    """monto=100 con deuda_actual=50 → ValidacionError, NO se llama pagos.crear ni incrementar_deuda_atomic."""

    async def _run():
        proveedores = MockProveedorRepository()
        pagos = MockPagoProveedorRepository()
        proveedores.add_proveedor(
            Proveedor(
                id=None,
                razon_social="P",
                creado_por=1,
                creado_por_nombre="A",
                deuda_actual=Decimal("50.00"),
            )
        )
        use_case = RegistrarPagoProveedorUseCase(
            proveedor_repo=proveedores,
            pago_repo=pagos,
            auditoria=make_auditoria_mock(),
        )
        prov_id = next(iter(proveedores._proveedores.keys()))
        with pytest.raises(ValidacionError) as exc:
            await use_case.ejecutar(
                proveedor_id=prov_id,
                monto=Decimal("100.00"),
                fecha=date(2026, 7, 25),
                concepto=None,
                usuario_id=1,
                usuario_nombre="X",
            )
        assert "superar la deuda" in str(exc.value).lower()
        assert pagos.crear_call_count == 0
        assert proveedores.incrementar_deuda_atomic_call_count == 0

    asyncio.run(_run())
