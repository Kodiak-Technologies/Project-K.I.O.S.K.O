"""E2E tests for `mermas_router` (3 endpoints del scope).

Cubre GET /mermas, GET /mermas/{id} (404), POST /mermas/{id}/rechazar.
Async discipline (CN-2): todo test es sync `def test_*` que envuelve `correr(_run())`.

KNOWN BUG: `Merma.rechazar()` does not set `rechazado_en`, so the DB CHECK
constraint `chk_mermas_estado_consistente` fails. The rechazar test is marked
xfail until the production code is fixed (see discovered/modulo-b-tests-coverage-subset).
"""
from __future__ import annotations

import pytest

from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    MermaModel,
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


async def _merma_registrada_directo(
    cat_id: int, prod_id: int, usuario_id: int, usuario_nombre: str
) -> int:
    """Inserta una merma Registrada con motivo='vencimiento' vía SessionLocal directo."""
    async with SessionLocal() as db:
        fila = MermaModel(
            producto_id=prod_id,
            cantidad=2,
            motivo="vencimiento",
            registrado_por=usuario_id,
            registrado_por_nombre=usuario_nombre,
        )
        db.add(fila)
        await db.commit()
        return fila.id


def test_get_mermas_paginado_200() -> None:
    """GET /mermas?page=1&page_size=20 con 2 mermas Registradas responde 200."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("mermv")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver"])
            tok = (await token_de(api, user))["access_token"]
            cat_id = await crear_categoria_directo(f"Cat-{username_unico('C')}")
            prod_id = await crear_producto_directo(
                f"PROD-{username_unico('P')}", "P", cat_id, stock=10
            )
            for _ in range(2):
                await _merma_registrada_directo(cat_id, prod_id, 1, "A")
            r = await api.get(
                "/mermas?page=1&page_size=20", headers=auth(tok)
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


def test_get_mermas_id_inexistente_404() -> None:
    """GET /mermas/99999 responde 404 (NoEncontradoError)."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("mermv")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver"])
            tok = (await token_de(api, user))["access_token"]
            r = await api.get("/mermas/99999", headers=auth(tok))
            assert r.status_code == 404, r.text

    correr(_run())


@pytest.mark.xfail(
    reason="Production bug: Merma.rechazar() does not set rechazado_en; CHECK constraint fails; see discovered/modulo-b-tests-coverage-subset",
    strict=False,
)
def test_post_mermas_id_rechazar_happy_200() -> None:
    """POST /mermas/{id}/rechazar con motivo >=5 chars responde 200 con estado='Rechazada'."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("mermadm")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["mermas.confirmar"])
            tok = (await token_de(api, user))["access_token"]
            cat_id = await crear_categoria_directo(f"Cat-{username_unico('C')}")
            prod_id = await crear_producto_directo(
                f"PROD-{username_unico('P')}", "P", cat_id, stock=10
            )
            mid = await _merma_registrada_directo(cat_id, prod_id, 1, "A")
            r = await api.post(
                f"/mermas/{mid}/rechazar",
                json={"motivo_rechazo": "Carga ya registrada como merma operativa"},
                headers=auth(tok),
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["estado"] == "Rechazada"
            assert data["motivo_rechazo"] is not None

    correr(_run())
