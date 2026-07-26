"""E2E tests for `categorias_router` (CN-7: reusa conftest existente).

Cubre los 3 endpoints del scope: GET, POST, PATCH contra la BD real `kiosko-test`.
Async discipline (CN-2): todo test es sync `def test_*` que envuelve `correr(_run())`.

BUG CORREGIDO: `sqlalchemy_categoria_repository.actualizar()` usaba `scalar_one()`
(500 en vez de 404) y leía `updated_at` tras el flush sin refrescar (MissingGreenlet,
500 en el camino feliz). Los 2 tests de PATCH ya no son xfail: son la regresión.
"""
from __future__ import annotations

import pytest

from .conftest import (
    asignar_permisos,
    auth,
    cliente_api,
    correr,
    crear_categoria_directo,
    crear_usuario_directo,
    token_de,
    username_unico,
)


def test_get_categorias_vacio_200() -> None:
    """GET /categorias responde 200 (lista puede tener [] o categorías preexistentes)."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("cat")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver"])
            tok = (await token_de(api, user))["access_token"]
            r = await api.get("/categorias", headers=auth(tok))
            assert r.status_code == 200, r.text
            assert isinstance(r.json(), list)

    correr(_run())


def test_get_categorias_con_preexistentes_200() -> None:
    """2 categorías creadas vía crear_categoria_directo aparecen en GET /categorias."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("cat")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver"])
            tok = (await token_de(api, user))["access_token"]
            nombres = {f"Cat-{username_unico('X')}" for _ in range(2)}
            ids = set()
            for n in nombres:
                ids.add(await crear_categoria_directo(n))
            r = await api.get("/categorias", headers=auth(tok))
            assert r.status_code == 200
            items = r.json()
            nombres_resp = {c["nombre"] for c in items}
            assert nombres.issubset(nombres_resp)

    correr(_run())


def test_post_categorias_nombre_unico_201() -> None:
    """POST /categorias con nombre único responde 201 con id y nombre."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("catadm")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["inventario.ver", "categorias.gestionar"])
            tok = (await token_de(api, user))["access_token"]
            nombre = f"Cat-{username_unico('N')}"
            r = await api.post("/categorias", json={"nombre": nombre}, headers=auth(tok))
            assert r.status_code == 201, r.text
            data = r.json()
            assert data["nombre"] == nombre
            assert data["id"] > 0

    correr(_run())


def test_post_categorias_duplicado_409() -> None:
    """POST /categorias con nombre duplicado responde 409 (ConflictoError)."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("catadm")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["categorias.gestionar"])
            tok = (await token_de(api, user))["access_token"]
            nombre = f"Cat-{username_unico('D')}"
            await crear_categoria_directo(nombre)
            r = await api.post("/categorias", json={"nombre": nombre}, headers=auth(tok))
            assert r.status_code == 409, r.text

    correr(_run())


def test_patch_categorias_happy_200() -> None:
    """PATCH /categorias/{id} con nombre nuevo responde 200 con la categoría actualizada."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("catadm")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["categorias.gestionar"])
            tok = (await token_de(api, user))["access_token"]
            nombre_orig = f"Cat-{username_unico('O')}"
            cid = await crear_categoria_directo(nombre_orig)
            nombre_nuevo = f"Cat-{username_unico('N')}"
            r = await api.patch(
                f"/categorias/{cid}",
                json={"nombre": nombre_nuevo},
                headers=auth(tok),
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["nombre"] == nombre_nuevo
            assert data["id"] == cid

    correr(_run())


def test_patch_categorias_id_inexistente_404() -> None:
    """PATCH /categorias/99999 responde 404 (NoEncontradoError)."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("catadm")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["categorias.gestionar"])
            tok = (await token_de(api, user))["access_token"]
            r = await api.patch(
                "/categorias/99999",
                json={"nombre": f"Cat-{username_unico('X')}"},
                headers=auth(tok),
            )
            assert r.status_code == 404, r.text

    correr(_run())
