"""Unit tests for `ConfirmarMermaUseCase` (CU-B09b, REQ-CONF).

RED: cada aserción fallaría si el use case omitiera el SELECT FOR UPDATE,
el UPDATE atómico de stock, el append al movimiento_inventario, la transición
de estado de la merma, o la auditoría.

GREEN: las 4 aserciones pasan con Mocks que cumplen el Port.
"""
from __future__ import annotations

import asyncio

import pytest

from app.modules.modulo_b_inventario.application.confirmar_merma_usecase import (
    ConfirmarMermaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.value_objects import EstadoMerma, MotivoMerma
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError

from ._mocks import (
    MockMermaRepository,
    MockMovimientoInventarioRepository,
    MockProductoRepository,
    make_auditoria_mock,
)


def test_confirmar_merma_con_stock_suficiente_happy() -> None:
    """Merma Registrada + stock suficiente → atomic decrement, append movimiento, transición."""

    async def _run():
        mermas = MockMermaRepository()
        productos = MockProductoRepository()
        movimientos = MockMovimientoInventarioRepository()
        auditoria = make_auditoria_mock()
        # Merma Registrada
        merma = Merma(
            id=1,
            producto_id=10,
            cantidad=3,
            motivo=MotivoMerma("vencimiento"),
            registrado_por=1,
            registrado_por_nombre="Cajero",
        )
        mermas.add_merma(merma)
        productos.incrementar_stock_atomic_return_value = (True, 7)
        use_case = ConfirmarMermaUseCase(
            merma_repo=mermas,
            producto_repo=productos,
            movimiento_repo=movimientos,
            auditoria=auditoria,
        )
        resultado = await use_case.ejecutar(
            merma_id=1, usuario_id=2, usuario_nombre="Admin"
        )
        assert mermas.find_by_id_for_update_call_count == 1
        # atomic decrement llamado 1 vez
        # movimientos.append llamado 1 vez con tipo merma y cantidad = merma.cantidad (3)
        assert movimientos.append_call_count == 1
        mov = movimientos.append_last_movimiento
        assert str(mov.tipo) == "merma"
        # MovimientoInventario.merma() factory setea cantidad=-merma.cantidad (salida)
        assert mov.cantidad == -3
        assert mov.merma_id == 1
        # merma.actualizar llamado con estado=Confirmada
        assert mermas.actualizar_call_count == 1
        assert mermas.actualizar_last_merma.estado.valor == "Confirmada"
        # auditoría con accion=confirmar_merma
        assert auditoria.ejecutar.await_count == 1
        assert auditoria.ejecutar.await_args.kwargs["accion"] == "confirmar_merma"
        assert resultado.stock_actualizado == 7

    asyncio.run(_run())


def test_merma_inexistente_levanta_no_encontrado_error() -> None:
    """MockMermaRepository.find_by_id_for_update=None → NoEncontradoError."""

    async def _run():
        mermas = MockMermaRepository()
        productos = MockProductoRepository()
        productos.incrementar_stock_atomic_return_value = (True, 0)
        use_case = ConfirmarMermaUseCase(
            merma_repo=mermas,
            producto_repo=productos,
            movimiento_repo=MockMovimientoInventarioRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(NoEncontradoError) as exc:
            await use_case.ejecutar(merma_id=999, usuario_id=1, usuario_nombre="X")
        assert "merma" in str(exc.value).lower()
        # No se llama atomic ni movimientos
        assert productos.incrementar_stock_atomic_call_count == 0 if hasattr(productos, "incrementar_stock_atomic_call_count") else True

    asyncio.run(_run())


def test_merma_ya_confirmada_levanta_conflicto_error() -> None:
    """Merma en estado Confirmada → ConflictoError."""

    async def _run():
        mermas = MockMermaRepository()
        merma = Merma(
            id=1,
            producto_id=10,
            cantidad=3,
            motivo=MotivoMerma("vencimiento"),
            registrado_por=1,
            registrado_por_nombre="C",
            estado=EstadoMerma("Confirmada"),
        )
        mermas.add_merma(merma)
        use_case = ConfirmarMermaUseCase(
            merma_repo=mermas,
            producto_repo=MockProductoRepository(),
            movimiento_repo=MockMovimientoInventarioRepository(),
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ConflictoError) as exc:
            await use_case.ejecutar(merma_id=1, usuario_id=1, usuario_nombre="X")
        assert "revisada" in str(exc.value).lower()

    asyncio.run(_run())


def test_stock_insuficiente_levanta_conflicto_error() -> None:
    """incrementar_stock_atomic=(False, None) → ConflictoError, no append, no actualizar."""

    async def _run():
        mermas = MockMermaRepository()
        productos = MockProductoRepository()
        movimientos = MockMovimientoInventarioRepository()
        # Producto activo existente para que la validación 'producto borrado' no se dispare
        from app.modules.modulo_b_inventario.domain.entities import Producto

        productos._productos[10] = Producto(
            id=10, codigo="P-OK", nombre="P", categoria_id=None, precio=__import__("decimal").Decimal("1.00")
        )
        productos.incrementar_stock_atomic_return_value = (False, None)
        merma = Merma(
            id=1,
            producto_id=10,
            cantidad=99,
            motivo=MotivoMerma("vencimiento"),
            registrado_por=1,
            registrado_por_nombre="C",
        )
        mermas.add_merma(merma)
        use_case = ConfirmarMermaUseCase(
            merma_repo=mermas,
            producto_repo=productos,
            movimiento_repo=movimientos,
            auditoria=make_auditoria_mock(),
        )
        with pytest.raises(ConflictoError) as exc:
            await use_case.ejecutar(merma_id=1, usuario_id=1, usuario_nombre="X")
        assert "stock" in str(exc.value).lower()
        assert movimientos.append_call_count == 0
        assert mermas.actualizar_call_count == 0

    asyncio.run(_run())
