"""Unit tests for `SolicitudIngreso.aprobar` and `SolicitudIngreso.rechazar` (D-09).

Bug #2 from `modulo-b-bugfixes-verify`:
  `aprobar()` and `rechazar()` set `revisado_por` and `revisado_por_nombre`,
  but they DID NOT set `revisado_en`. The DB CHECK constraint
  `chk_solicitudes_revisado_consistente` requires `revisado_en IS NOT NULL`
  for terminal states (`Aprobada`, `Rechazada`), so the UPDATE failed with
  `asyncpg.exceptions.CheckViolationError` → HTTP 500.

Strict TDD: these tests were written FIRST. They MUST fail on the unmodified
`entities.py` (RED) and MUST pass after the fix (GREEN).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.modules.modulo_b_inventario.application.aprobar_ingreso_usecase import (
    AprobarIngresoUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    DetalleSolicitud,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud


# =============================================================================
# Helpers
# =============================================================================


def _solicitud_pendiente(solicitud_id: int = 1) -> SolicitudIngreso:
    """Build a Pendiente SolicitudIngreso with the minimum required fields."""
    return SolicitudIngreso(
        id=solicitud_id,
        estado=EstadoSolicitud("Pendiente"),
        foto_boleta_url="https://example.test/boleta.jpg",
        solicitado_por=10,
        solicitado_por_nombre="Cajero Demo",
    )


# =============================================================================
# T1.1a — entity-level: aprobar() must set revisado_en close to now
# =============================================================================


def test_aprobar_sets_revisado_en_close_to_now() -> None:
    """After `aprobar(usuario_id, usuario_nombre)`:
    - `estado` becomes "Aprobada"
    - `revisado_por` equals the user id
    - `revisado_por_nombre` equals the user name
    - `revisado_en` is a UTC datetime within 5 seconds of now.
    """
    antes = datetime.now(timezone.utc)
    solicitud = _solicitud_pendiente()
    assert solicitud.revisado_en is None  # precondition: pendiente → revisado_en is None

    solicitud.aprobar(usuario_id=42, nombre="Admin Demo")

    despues = datetime.now(timezone.utc)
    assert solicitud.estado == EstadoSolicitud("Aprobada")
    assert solicitud.revisado_por == 42
    assert solicitud.revisado_por_nombre == "Admin Demo"
    assert solicitud.revisado_en is not None
    assert isinstance(solicitud.revisado_en, datetime)
    # UTC tzinfo guard
    assert solicitud.revisado_en.tzinfo is not None
    assert solicitud.revisado_en.utcoffset() == timezone.utc.utcoffset(solicitud.revisado_en)
    # Within 5 seconds of now
    delta = (despues - solicitud.revisado_en).total_seconds()
    assert 0.0 <= delta <= 5.0, f"revisado_en delta = {delta}s, expected [0, 5]"


# =============================================================================
# T1.1b — entity-level: rechazar() must set revisado_en close to now
# =============================================================================


def test_rechazar_sets_revisado_en_close_to_now() -> None:
    """After `rechazar(usuario_id, usuario_nombre, motivo)`:
    - `estado` becomes "Rechazada"
    - motivo is stored
    - `revisado_por`, `revisado_por_nombre` are set
    - `revisado_en` is a UTC datetime within 5 seconds of now.
    """
    antes = datetime.now(timezone.utc)
    solicitud = _solicitud_pendiente()
    assert solicitud.revisado_en is None  # precondition

    solicitud.rechazar(
        usuario_id=7, nombre="Admin Demo", motivo="Boleta ilegible, no se puede validar"
    )

    despues = datetime.now(timezone.utc)
    assert solicitud.estado == EstadoSolicitud("Rechazada")
    assert solicitud.revisado_por == 7
    assert solicitud.revisado_por_nombre == "Admin Demo"
    assert solicitud.motivo_rechazo == "Boleta ilegible, no se puede validar"
    assert solicitud.revisado_en is not None
    assert isinstance(solicitud.revisado_en, datetime)
    assert solicitud.revisado_en.tzinfo is not None
    assert solicitud.revisado_en.utcoffset() == timezone.utc.utcoffset(solicitud.revisado_en)
    delta = (despues - solicitud.revisado_en).total_seconds()
    assert 0.0 <= delta <= 5.0, f"revisado_en delta = {delta}s, expected [0, 5]"


# =============================================================================
# T1.1c — use case: aprobar_ingreso persists revisado_en to the repository
# =============================================================================


def test_aprobar_use_case_persists_revisado_en() -> None:
    """The `AprobarIngresoUseCase` MUST call the repository's `actualizar(solicitud)`
    with a `solicitud` whose `revisado_en` is set. Otherwise the DB CHECK constraint
    will reject the UPDATE with HTTP 500.
    """
    # Build a real Pendiente solicitud (this is what the repo will return)
    solicitud_in_db = _solicitud_pendiente(solicitud_id=99)

    detalle = DetalleSolicitud(
        id=None,
        solicitud_id=99,
        producto_id=1,
        cantidad=5,
        precio_compra_unitario=Decimal("10.00"),
    )

    # Mock all 4 repository ports + auditoria
    solicitud_repo = AsyncMock()
    solicitud_repo.find_by_id_for_update = AsyncMock(return_value=solicitud_in_db)
    solicitud_repo.actualizar = AsyncMock(
        side_effect=lambda s: s  # passthrough: returns the same solicitud
    )

    detalle_repo = AsyncMock()
    detalle_repo.listar_por_solicitud = AsyncMock(return_value=[detalle])

    producto_repo = AsyncMock()
    producto_repo.incrementar_stock_atomic = AsyncMock(return_value=(True, 15))

    movimiento_repo = AsyncMock()
    movimiento_repo.append = AsyncMock(return_value=None)

    auditoria = AsyncMock()
    auditoria.ejecutar = AsyncMock(return_value=None)

    use_case = AprobarIngresoUseCase(
        solicitud_repo=solicitud_repo,
        detalle_repo=detalle_repo,
        producto_repo=producto_repo,
        movimiento_repo=movimiento_repo,
        auditoria=auditoria,
    )

    resultado = asyncio.run(
        use_case.ejecutar(
            solicitud_id=99,
            usuario_id=42,
            usuario_nombre="Admin Demo",
        )
    )

    # The mock `actualizar` was called exactly once
    assert solicitud_repo.actualizar.await_count == 1
    # The argument passed was the (mutated) solicitud
    arg = solicitud_repo.actualizar.await_args
    assert arg is not None
    solicitud_persisted = arg.args[0]
    # THE ASSERTION THAT FAILED BEFORE THE FIX:
    assert solicitud_persisted.revisado_en is not None, (
        "Bug #2 NOT fixed: aprobar_ingreso_usecase persisted a solicitud with "
        "revisado_en IS NULL, which violates chk_solicitudes_revisado_consistente."
    )
    assert isinstance(solicitud_persisted.revisado_en, datetime)
    assert solicitud_persisted.estado == EstadoSolicitud("Aprobada")
    assert solicitud_persisted.revisado_por == 42
    assert solicitud_persisted.revisado_por_nombre == "Admin Demo"
    # Sanity: the returned solicitud from the use case also reflects the transition
    assert resultado.solicitud.revisado_en is not None
    assert resultado.solicitud.estado == EstadoSolicitud("Aprobada")
