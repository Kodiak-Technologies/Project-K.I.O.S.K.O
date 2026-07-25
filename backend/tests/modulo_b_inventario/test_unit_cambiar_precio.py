"""Unit tests for `SqlAlchemyProductoRepository.actualizar_precio` (Bug #1).

Bug #1 from `modulo-b-bugfixes-verify`:
  `actualizar_precio` built the `HistorialPrecio` domain entity via
  `_historial_a_entidad(hist)` **before** `await self._db.flush()`. At that
  point the SQLAlchemy model has no DB-assigned `id`, so the entity carried
  `id=None`. The strict `id: int` schema in `HistorialPrecioResponse` then
  failed with Pydantic `ValidationError`, surfacing as HTTP 500.

Strict TDD: these tests were written FIRST and they MUST fail on the
unmodified `actualizar_precio` (RED) and MUST pass after the reorder fix
(GREEN).

Strategy: the test drives the REAL `actualizar_precio` method but mocks the
`AsyncSession` with `AsyncMock`. The mock simulates the DB by assigning a
real `id` to each `HistorialPrecioModel` when `flush()` is awaited. The bug
is observable because the entity is built BEFORE `flush()` in the original
code (so its `id` is still `None`), and is built AFTER `flush()` in the fix
(so its `id` is the simulated DB-assigned value).
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    HistorialPrecioModel,
    ProductoModel,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_producto_repository import (
    SqlAlchemyProductoRepository,
)


def _build_mock_session(producto_model: ProductoModel) -> MagicMock:
    """Build a mock AsyncSession that simulates the DB for `actualizar_precio`.

    The mock handles:
      1. First `execute()`: SELECT ... FOR UPDATE → returns `producto_model`
         via `scalar_one_or_none()`.
      2. `flush()`: assigns a real `id` (123) to any HistorialPrecioModel
         that was added (simulates the DB-assigned PK).
      3. Second `execute()`: called from `buscar_por_id()` after flush →
         returns a tuple `(producto_model, categoria_nombre)` via `first()`.
    """
    db = MagicMock()
    db.add = MagicMock()

    # Assign simulated DB PKs on flush
    async def fake_flush() -> None:
        for call in db.add.call_args_list:
            fila = call.args[0]
            if isinstance(fila, HistorialPrecioModel) and fila.id is None:
                fila.id = 123  # simulated DB-assigned id

    db.flush = AsyncMock(side_effect=fake_flush)

    # Two distinct execute() results: FOR UPDATE then buscar_por_id
    execute_calls = {"n": 0}

    async def execute_side_effect(*args, **kwargs):
        execute_calls["n"] += 1
        if execute_calls["n"] == 1:
            # SELECT ... FOR UPDATE
            r = MagicMock()
            r.scalar_one_or_none = MagicMock(return_value=producto_model)
            return r
        # buscar_por_id (after flush)
        r = MagicMock()
        r.first = MagicMock(return_value=(producto_model, "Cat-Test"))
        return r

    db.execute = AsyncMock(side_effect=execute_side_effect)
    return db


def test_cambiar_precio_response_includes_real_ids() -> None:
    """After `actualizar_precio`, `filas_historial[0].id` MUST be a real int.

    Bug #1: before the fix, the entity was built before flush so `id` was None.
    After the fix, the entity is built after flush so `id` is the DB-assigned int.
    """
    # Arrange: a real ProductoModel with the initial precio
    producto_model = ProductoModel(
        id=42,
        codigo="P-TEST-1",
        nombre="Test Producto",
        categoria_id=1,
        precio=Decimal("10.00"),
        precio_compra_actual=Decimal("5.00"),
        stock=10,
        stock_minimo=1,
    )
    db = _build_mock_session(producto_model)
    repo = SqlAlchemyProductoRepository(db)

    # Act: call the real actualizar_precio with a new precio_venta
    producto_actualizado, filas_historial = asyncio.run(
        repo.actualizar_precio(
            producto_id=42,
            precio_venta=Decimal("20.00"),
            precio_compra_actual=None,
            usuario_id=1,
            usuario_nombre="Admin Test",
        )
    )

    # Assert: there should be exactly 1 historial row, and its id MUST be a real int
    assert len(filas_historial) == 1
    hist = filas_historial[0]
    assert hist.id is not None, (
        "Bug #1 NOT fixed: actualizar_precio returned a HistorialPrecio entity "
        "with id=None (entity was built before flush). This breaks the strict "
        "id: int contract in HistorialPrecioResponse and surfaces as HTTP 500."
    )
    assert hist.id == 123  # the simulated DB-assigned id from fake_flush
    assert hist.producto_id == 42
    assert hist.precio_anterior == Decimal("10.00")
    assert hist.precio_nuevo == Decimal("20.00")
    assert str(hist.tipo_precio) == "venta"


def test_cambiar_precio_response_no_none_ids() -> None:
    """Regression guard: NO entry in `filas_historial` may have `id=None`.

    This test simulates the case where BOTH precio_venta and precio_compra_actual
    change, producing 2 historial rows. Even with multiple rows, every entity
    built by the adapter must have a real id.
    """
    producto_model = ProductoModel(
        id=99,
        codigo="P-TEST-2",
        nombre="Test Producto 2",
        categoria_id=1,
        precio=Decimal("10.00"),
        precio_compra_actual=Decimal("5.00"),
        stock=10,
        stock_minimo=1,
    )
    db = _build_mock_session(producto_model)
    repo = SqlAlchemyProductoRepository(db)

    # Act: change BOTH prices, should produce 2 historial rows
    producto_actualizado, filas_historial = asyncio.run(
        repo.actualizar_precio(
            producto_id=99,
            precio_venta=Decimal("15.00"),
            precio_compra_actual=Decimal("7.00"),
            usuario_id=2,
            usuario_nombre="Admin Test 2",
        )
    )

    # Assert: 2 rows, both with real ids
    assert len(filas_historial) == 2
    none_ids = [i for i, h in enumerate(filas_historial) if h.id is None]
    assert none_ids == [], (
        f"Bug #1 NOT fixed: filas_historial contains None ids at positions {none_ids}. "
        "All entities must carry a real int id after flush."
    )
    # Each id is a positive int
    for h in filas_historial:
        assert isinstance(h.id, int)
        assert h.id > 0
