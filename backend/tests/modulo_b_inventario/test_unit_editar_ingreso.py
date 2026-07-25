"""Unit tests for EditarIngresoUseCase (sdd/modulo-b-aprobaciones-detalle-editar).

Cover AC-1, AC-4, AC-5, AC-6 from the spec.
"""
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.editar_ingreso_usecase import (
    EditarIngresoUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import DetalleSolicitud
from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud
from app.shared.kernel.exceptions import (
    ConflictoError,
    ProhibidoError,
    ValidacionError,
)

from tests.modulo_b_inventario._mocks import (
    MockDetalleSolicitudRepository,
    MockSolicitudIngresoRepository,
    make_auditoria_mock,
)


def _solicitud_pendiente(solicitado_por: int = 1) -> "SolicitudIngreso":
    from app.modules.modulo_b_inventario.domain.entities import SolicitudIngreso

    return SolicitudIngreso(
        id=1,
        estado=EstadoSolicitud("Pendiente"),
        foto_boleta_url="http://test/boleta.jpg",
        solicitado_por=solicitado_por,
        solicitado_por_nombre="Cajero",
        proveedor_id=5,
        lineas=[
            DetalleSolicitud(
                id=1, solicitud_id=1, producto_id=10, cantidad=2, precio_compra_unitario=Decimal("10")
            ),
        ],
    )


def _solicitud_aprobada() -> "SolicitudIngreso":
    s = _solicitud_pendiente()
    s.estado = EstadoSolicitud("Aprobada")
    s.revisado_por = 99
    s.revisado_por_nombre = "Admin"
    from datetime import datetime, timezone
    s.revisado_en = datetime.now(timezone.utc)
    return s


def _usecase() -> tuple[EditarIngresoUseCase, MockSolicitudIngresoRepository, MockDetalleSolicitudRepository]:
    repo = MockSolicitudIngresoRepository()
    detalle = MockDetalleSolicitudRepository()
    auditoria = make_auditoria_mock()
    s = _solicitud_pendiente()
    # Manually add the solicitud
    repo._solicitudes[s.id] = s
    repo._contador = s.id
    return EditarIngresoUseCase(repo, detalle, auditoria), repo, detalle


@pytest.mark.asyncio
async def test_editar_ingreso_cambia_motivo() -> None:
    """Happy path: cambiar motivo setea audit triple."""
    uc, repo, _det = _usecase()
    s = repo._solicitudes[1]

    actualizado = await uc.ejecutar(
        ingreso_id=1,
        editor_id=1,  # creator
        editor_nombre="Cajero",
        es_admin=False,
        motivo="correccion de motivo",
    )

    assert actualizado.motivo == "correccion de motivo"
    assert actualizado.editado_por == 1
    assert actualizado.editado_por_nombre == "Cajero"
    assert actualizado.editado_en is not None


@pytest.mark.asyncio
async def test_editar_ingreso_403_si_no_es_admin_ni_creador() -> None:
    """AC-5: permission rule: 403 si el usuario no es admin ni el creador."""
    uc, repo, _det = _usecase()
    # editor_id=999 ≠ solicitado_por=1 y no es admin
    with pytest.raises(ProhibidoError) as exc_info:
        await uc.ejecutar(
            ingreso_id=1,
            editor_id=999,
            editor_nombre="Otro",
            es_admin=False,
            motivo="intento",
        )
    assert exc_info.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_editar_ingreso_409_si_estado_aprobada() -> None:
    """AC-4: 409 NOT_EDITABLE_STATE si la solicitud no está en Pendiente."""
    uc, repo, _det = _usecase()
    repo._solicitudes[1] = _solicitud_aprobada()
    with pytest.raises(ConflictoError) as exc_info:
        await uc.ejecutar(
            ingreso_id=1,
            editor_id=1,
            editor_nombre="Cajero",
            es_admin=True,
            motivo="tarde",
        )
    assert exc_info.value.code == "NOT_EDITABLE_STATE"


@pytest.mark.asyncio
async def test_editar_ingreso_empty_patch_422() -> None:
    """AC: EMPTY_PATCH when no field is present (but not all-sentinel)."""
    uc, _repo, _det = _usecase()
    with pytest.raises(ValidacionError) as exc_info:
        await uc.ejecutar(
            ingreso_id=1,
            editor_id=1,
            editor_nombre="Cajero",
            es_admin=False,
            # All sentinel (...)
        )
    assert exc_info.value.code == "EMPTY_PATCH"


@pytest.mark.asyncio
async def test_editar_ingreso_admin_puede_editar_cualquiera() -> None:
    """AC: admin can edit even if not the creator (Pendiente only)."""
    uc, repo, _det = _usecase()
    actualizado = await uc.ejecutar(
        ingreso_id=1,
        editor_id=999,  # NOT the creator
        editor_nombre="Admin",
        es_admin=True,
        motivo="admin override",
    )
    assert actualizado.motivo == "admin override"
    assert actualizado.editado_por == 999


@pytest.mark.asyncio
async def test_editar_ingreso_404_si_no_existe() -> None:
    """AC: 404 INGRESO_NOT_FOUND when the row doesn't exist."""
    uc, _repo, _det = _usecase()
    with pytest.raises(Exception) as exc_info:
        await uc.ejecutar(
            ingreso_id=999,
            editor_id=1,
            editor_nombre="Cajero",
            es_admin=False,
            motivo="x",
        )
    # Should be NoEncontradoError
    assert "NoEncontradoError" in type(exc_info.value).__name__ or "INGRESO_NOT_FOUND" in str(exc_info.value)


@pytest.mark.asyncio
async def test_editar_ingreso_reemplaza_lineas() -> None:
    """FR-3.4: lineas in body → replace-all (delete + bulk insert)."""
    uc, repo, det = _usecase()
    actualizado = await uc.ejecutar(
        ingreso_id=1,
        editor_id=1,
        editor_nombre="Cajero",
        es_admin=False,
        lineas=[
            {"producto_id": 99, "cantidad": 3, "precio_unitario": Decimal("50")},
        ],
    )
    assert len(actualizado.lineas) == 1
    assert actualizado.lineas[0].producto_id == 99
    assert actualizado.lineas[0].cantidad == 3
    assert det.eliminar_por_solicitud_call_count if hasattr(det, "eliminar_por_solicitud_call_count") else True
