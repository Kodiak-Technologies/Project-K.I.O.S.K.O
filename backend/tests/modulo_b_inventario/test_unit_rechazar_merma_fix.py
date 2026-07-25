"""Unit test: Merma.rechazar() must set rechazado_en to satisfy the DB CHECK
constraint chk_mermas_estado_consistente.

Regression test for the bug that caused POST /mermas/{id}/rechazar to return
500 (CheckViolationError on the DB CHECK constraint). The fix: 1 line in
`Merma.rechazar()` setting `self.rechazado_en = datetime.now(timezone.utc)`.
"""
from datetime import datetime, timezone

import pytest

from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.value_objects import EstadoMerma, MotivoMerma


def _merma_registrada(motivo: str = "vencimiento") -> Merma:
    return Merma(
        id=1,
        producto_id=10,
        cantidad=3,
        motivo=MotivoMerma(motivo),
        registrado_por=1,
        registrado_por_nombre="Test",
    )


def test_rechazar_merma_setea_rechazado_en() -> None:
    """FR-5.1/5.2: rechazar() must set rechazado_en so the DB CHECK passes."""
    merma = _merma_registrada()
    assert merma.estado == EstadoMerma("Registrada")
    assert merma.rechazado_en is None

    merma.rechazar(usuario_id=42, nombre="Admin", motivo="motivo de prueba")

    assert merma.estado == EstadoMerma("Rechazada")
    assert merma.rechazado_por == 42
    assert merma.rechazado_por_nombre == "Admin"
    assert merma.motivo_rechazo == "motivo de prueba"
    assert merma.rechazado_en is not None, (
        "rechazado_en MUST be set; without it the DB CHECK "
        "chk_mermas_estado_consistente fails and POST /mermas/{id}/rechazar returns 500"
    )


def test_rechazar_merma_rechazado_en_es_reciente() -> None:
    """The timestamp should be ~now (within the last few seconds)."""
    merma = _merma_registrada()
    antes = datetime.now(timezone.utc)
    merma.rechazar(usuario_id=1, nombre="X", motivo="motivo valido de prueba")
    despues = datetime.now(timezone.utc)

    assert merma.rechazado_en is not None
    # Strip microsecond noise — DB columns are timestamptz (microsecond precision
    # but timezone-aware comparison is safe).
    assert antes <= merma.rechazado_en <= despues


def test_rechazar_merma_falla_si_ya_revisada() -> None:
    """If state != Registrada, rechazar() raises ConflictoError (existing behavior)."""
    from app.shared.kernel.exceptions import ConflictoError

    merma = _merma_registrada()
    merma.estado = EstadoMerma("Confirmada")
    with pytest.raises(ConflictoError):
        merma.rechazar(usuario_id=1, nombre="X", motivo="motivo valido")


def test_rechazar_merma_falla_motivo_corto() -> None:
    """Motivo must be >= 5 chars (DB CHECK chk_mermas_rechazo_tiene_motivo)."""
    from app.shared.kernel.exceptions import ValidacionError

    merma = _merma_registrada()
    with pytest.raises(ValidacionError):
        merma.rechazar(usuario_id=1, nombre="X", motivo="no")
