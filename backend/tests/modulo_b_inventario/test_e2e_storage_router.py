"""E2E tests for `storage_router` (2 escenarios, TRIMMED desde 3).

Cubre POST /storage/upload con `InMemoryStorageAdapter` (monkeypatch del singleton
`module_container._storage_adapter`) y el caso 403 sin permiso.

Recortado (diferido a follow-up): "POST productos 201" — el patrón es idéntico
al de boletas; si el primero pasa, el segundo está cubierto por simetría.

Disciplina async (CN-2): todo test es sync `def test_*` que envuelve `correr(_run())`.
Singleton (CN-5): monkeypatch.setattr(module_container, "_storage_adapter", InMemoryStorageAdapter()).
"""
from __future__ import annotations

import io

import pytest

from app.modules.modulo_b_inventario import module_container

from .conftest import (
    InMemoryStorageAdapter,
    asignar_permisos,
    auth,
    cliente_api,
    correr,
    crear_usuario_directo,
    token_de,
    username_unico,
)


@pytest.fixture
def storage_en_memoria(monkeypatch):
    """Fixture CN-5: monkeypatch del singleton `_storage_adapter`.

    El `StoragePort` no aparece en la firma del router, por lo que
    `app.dependency_overrides` no funciona. La única vía es monkeypatch
    del singleton módulo-level en `module_container`.
    """
    adapter = InMemoryStorageAdapter()
    monkeypatch.setattr(module_container, "_storage_adapter", adapter)
    return adapter


def test_post_storage_upload_boletas_201(storage_en_memoria) -> None:
    """POST /storage/upload con carpeta='boletas' responde 201 con path que empieza con 'boletas/'."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("stoadm")
            await crear_usuario_directo(user, "ADMIN")
            await asignar_permisos("ADMIN", ["storage.upload"])
            tok = (await token_de(api, user))["access_token"]
            file_content = b"\x89PNG_fake_image_data_for_test"
            files = {"file": ("test.png", io.BytesIO(file_content), "image/png")}
            r = await api.post(
                "/storage/upload",
                data={"carpeta": "boletas"},
                files=files,
                headers=auth(tok),
            )
            assert r.status_code == 201, r.text
            data = r.json()
            assert data["path"].startswith("boletas/")
            assert data["mime"] == "image/png"
            assert data["size_bytes"] == len(file_content)
            # InMemoryStorageAdapter fue llamado 1 vez con carpeta='boletas'
            assert len(storage_en_memoria.calls) == 1
            assert storage_en_memoria.calls[0]["carpeta"] == "boletas"

    correr(_run())


def test_post_storage_upload_sin_permiso_403(storage_en_memoria) -> None:
    """POST /storage/upload sin `storage.upload` responde 403 y el adapter NO se invoca."""

    async def _run():
        async with cliente_api() as api:
            user = username_unico("stocaj")
            await crear_usuario_directo(user, "CAJERO")
            # CAJERO con inventario.ver pero SIN storage.upload
            await asignar_permisos("CAJERO", ["inventario.ver"])
            tok = (await token_de(api, user))["access_token"]
            files = {"file": ("test.png", io.BytesIO(b"\x89PNG_x"), "image/png")}
            r = await api.post(
                "/storage/upload",
                data={"carpeta": "boletas"},
                files=files,
                headers=auth(tok),
            )
            assert r.status_code == 403, r.text
            # El guard rechaza ANTES de invocar el use case → adapter NO se llama
            assert storage_en_memoria.calls == []
