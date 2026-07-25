"""Unit tests for EditarMermaUseCase (sdd/modulo-b-aprobaciones-detalle-editar)."""
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.editar_merma_usecase import (
    EditarMermaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.value_objects import EstadoMerma, MotivoMerma
from app.shared.kernel.exceptions import (
    ConflictoError,
    ProhibidoError,
    ValidacionError,
)

from tests.modulo_b_inventario._mocks import MockMermaRepository, make_auditoria_mock


def _merma_registrada(registrado_por: int = 1) -> Merma:
    return Merma(
        id=1,
        producto_id=10,
        cantidad=3,
        motivo=MotivoMerma("vencimiento"),
        registrado_por=registrado_por,
        registrado_por_nombre="Cajero",
        estado=EstadoMerma("Registrada"),
        observacion="obs inicial",
    )


def _merma_confirmada() -> Merma:
    m = _merma_registrada()
    m.estado = EstadoMerma("Confirmada")
    m.confirmado_por = 99
    m.confirmado_por_nombre = "Admin"
    from datetime import datetime, timezone
    m.confirmado_en = datetime.now(timezone.utc)
    return m


@pytest.mark.asyncio
async def test_editar_merma_cambia_observacion_y_motivo() -> None:
    """Happy path."""
    repo = MockMermaRepository()
    merma = _merma_registrada()
    repo.add_merma(merma)
    uc = EditarMermaUseCase(repo, make_auditoria_mock())

    actualizado = await uc.ejecutar(
        merma_id=1,
        editor_id=1,
        editor_nombre="Cajero",
        es_admin=False,
        observacion="obs corregida",
        motivo="rotura",
    )

    assert actualizado.observacion == "obs corregida"
    assert str(actualizado.motivo) == "rotura"
    assert actualizado.editado_por == 1
    assert actualizado.editado_por_nombre == "Cajero"
    assert actualizado.editado_en is not None


@pytest.mark.asyncio
async def test_editar_merma_403_si_no_es_admin_ni_creador() -> None:
    repo = MockMermaRepository()
    repo.add_merma(_merma_registrada(registrado_por=1))
    uc = EditarMermaUseCase(repo, make_auditoria_mock())
    with pytest.raises(ProhibidoError) as exc_info:
        await uc.ejecutar(
            merma_id=1,
            editor_id=999,
            editor_nombre="Otro",
            es_admin=False,
            observacion="intento",
        )
    assert exc_info.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_editar_merma_409_si_confirmada() -> None:
    repo = MockMermaRepository()
    repo.add_merma(_merma_confirmada())
    uc = EditarMermaUseCase(repo, make_auditoria_mock())
    with pytest.raises(ConflictoError) as exc_info:
        await uc.ejecutar(
            merma_id=1,
            editor_id=999,
            editor_nombre="X",
            es_admin=True,
            observacion="tarde",
        )
    assert exc_info.value.code == "NOT_EDITABLE_STATE"


@pytest.mark.asyncio
async def test_editar_merma_empty_patch_422() -> None:
    repo = MockMermaRepository()
    repo.add_merma(_merma_registrada())
    uc = EditarMermaUseCase(repo, make_auditoria_mock())
    with pytest.raises(ValidacionError) as exc_info:
        await uc.ejecutar(
            merma_id=1,
            editor_id=1,
            editor_nombre="Cajero",
            es_admin=False,
        )
    assert exc_info.value.code == "EMPTY_PATCH"


@pytest.mark.asyncio
async def test_editar_merma_invalid_motivo_422() -> None:
    repo = MockMermaRepository()
    repo.add_merma(_merma_registrada())
    uc = EditarMermaUseCase(repo, make_auditoria_mock())
    with pytest.raises(ValidacionError) as exc_info:
        await uc.ejecutar(
            merma_id=1,
            editor_id=1,
            editor_nombre="Cajero",
            es_admin=False,
            motivo="roto",  # not in enum
        )
    assert exc_info.value.code == "INVALID_MOTIVO"


@pytest.mark.asyncio
async def test_editar_merma_invalid_cantidad_422() -> None:
    repo = MockMermaRepository()
    repo.add_merma(_merma_registrada())
    uc = EditarMermaUseCase(repo, make_auditoria_mock())
    with pytest.raises(ValidacionError) as exc_info:
        await uc.ejecutar(
            merma_id=1,
            editor_id=1,
            editor_nombre="Cajero",
            es_admin=False,
            cantidad=0,
        )
    assert exc_info.value.code == "INVALID_CANTIDAD"
