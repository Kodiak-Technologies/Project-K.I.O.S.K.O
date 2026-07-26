"""E2E tests for `ingresos_router` (3 endpoints del scope).

Cubre GET /ingresos, GET /ingresos/{id} (404), POST /ingresos/{id}/rechazar.
Async discipline (CN-2): todo test es sync `def test_*` que envuelve `correr(_run())`.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    DetalleSolicitudModel,
    SolicitudIngresoModel,
)
from app.shared.database.session import SessionLocal

from .conftest import (
    asignar_permisos,
    auth,
    cliente_api,
    correr,
    crear_categoria_directo,
    crear_producto_directo,
    crear_usuario_directo,
    token_de,
    username_unico,
)


async def _solicitud_pendiente_directo(
    cat_id: int, prod_id: int, usuario_id: int, usuario_nombre: str
) -> int:
    """Inserta una solicitud Pendiente con 1 detalle, vía SessionLocal directo."""
    async with SessionLocal() as db:
        fila = SolicitudIngresoModel(
            estado="Pendiente",
            foto_boleta_url=f"https://x.test/{username_unico('B')}.jpg",
            solicitado_por=usuario_id,
            solicitado_por_nombre=usuario_nombre,
            proveedor_id=None,
        )
        db.add(fila)
        await db.flush()
        db.add(
            DetalleSolicitudModel(
                solicitud_id=fila.id,
                producto_id=prod_id,
                cantidad=3,
                precio_compra_unitario=Decimal("10.00"),
            )
        )
        await db.commit()
        return fila.id


def test_get_ingresos_paginado_200() -> None:
    """GET /ingresos?page=1&page_size=20 con 2 solicitudes pendientes responde 200."""

    async def _run():
        async with cliente_api() as api:
            # Setup: usuario con permiso inventario.ver
            user = username_unico("ingv")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver"])
            tok = (await token_de(api, user))["access_token"]
            # Crear cat + producto + 2 solicitudes
            cat_id = await crear_categoria_directo(f"Cat-{username_unico('C')}")
            prod_id = await crear_producto_directo(
                f"PROD-{username_unico('P')}", "P", cat_id, stock=50
            )
            for _ in range(2):
                await _solicitud_pendiente_directo(
                    cat_id, prod_id, usuario_id=1, usuario_nombre="A"
                )
            r = await api.get(
                "/ingresos?page=1&page_size=20", headers=auth(tok)
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert "items" in data
            assert "total" in data
            assert data["total"] >= 2
            assert data["page"] == 1
            assert data["page_size"] == 20
            assert data["total_pages"] >= 1

    correr(_run())


def test_get_ingresos_id_inexistente_404() -> None:
    """GET /ingresos/99999 responde 404 (NoEncontradoError)."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("ingv")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver"])
            tok = (await token_de(api, user))["access_token"]
            r = await api.get("/ingresos/99999", headers=auth(tok))
            assert r.status_code == 404, r.text

    correr(_run())


def test_post_ingresos_id_rechazar_happy_200() -> None:
    """POST /ingresos/{id}/rechazar con motivo >=5 chars responde 200 con estado='Rechazada'."""

    async def _run():
        async with cliente_api() as api:
            # ADMIN con permiso inventario.aprobar_ingreso
            user = username_unico("ingadm")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.aprobar_ingreso"])
            tok = (await token_de(api, user))["access_token"]
            cat_id = await crear_categoria_directo(f"Cat-{username_unico('C')}")
            prod_id = await crear_producto_directo(
                f"PROD-{username_unico('P')}", "P", cat_id, stock=0
            )
            sid = await _solicitud_pendiente_directo(
                cat_id, prod_id, usuario_id=1, usuario_nombre="A"
            )
            r = await api.post(
                f"/ingresos/{sid}/rechazar",
                json={"motivo_rechazo": "Boleta ilegible, no se valida"},
                headers=auth(tok),
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["estado"] == "Rechazada"
            assert data["motivo_rechazo"] is not None

    correr(_run())
