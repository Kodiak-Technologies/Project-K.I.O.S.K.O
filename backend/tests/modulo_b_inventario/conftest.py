# Utilidades compartidas de los tests del Módulo B.
# Patrón del Módulo A: tests contra la BD real de DATABASE_URL.
from __future__ import annotations

import asyncio
import secrets
import sys
import uuid

import httpx
from sqlalchemy import select

from app.main import app
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    BitacoraAuditoriaModel,
    PermisoModel,
    RolModel,
    RolPermisoModel,
    UsuarioModel,
)
from app.modules.modulo_b_inventario.domain.ports.storage_port import StoragePort
from app.modules.modulo_b_inventario.domain.value_objects import StorageResult
from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
    CategoriaModel,
    ProductoModel,
)
from app.shared.database.session import SessionLocal, engine

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PASSWORD_PRUEBA = "Prueba1234"

# Hash bcrypt pre-computado de "Prueba1234" (bcrypt $2b$12 cost 12).
# Se hardcodea acá para evitar un bug conocido de passlib 1.7 + bcrypt 4.x
# que rompe el hashear al importar el backend (detect_wrap_bug falla).
_HASH_PRUEBA = "$2b$12$ESnwWTepcbY37Nt.MFgobuv08dQ8haLpq77U7cj5CmlsvsK/wucVS"


def correr(corutina):
    """Ejecuta la corutina y SIEMPRE libera el pool."""

    async def _con_limpieza():
        try:
            return await corutina
        finally:
            await engine.dispose()

    return asyncio.run(_con_limpieza())


def cliente_api() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def username_unico(prefijo: str) -> str:
    return f"{prefijo}_{secrets.token_hex(4)}"


async def crear_usuario_directo(
    username: str, rol_nombre: str, activo: bool = True
) -> int:
    """Inserta un usuario de prueba con hash pre-computado (sin pasar por auth)."""
    async with SessionLocal() as db:
        rol_id = (
            await db.execute(select(RolModel.id).where(RolModel.nombre == rol_nombre))
        ).scalar_one()
        fila = UsuarioModel(
            username=username,
            nombre=f"Usuario de prueba {username}",
            password_hash=_HASH_PRUEBA,
            rol_id=rol_id,
            activo=activo,
        )
        db.add(fila)
        await db.commit()
        return fila.id


async def asignar_permisos(rol_nombre: str, codigos: list[str]) -> None:
    """Asegura que el rol tenga los permisos indicados (idempotente)."""
    async with SessionLocal() as db:
        rol_id = (
            await db.execute(select(RolModel.id).where(RolModel.nombre == rol_nombre))
        ).scalar_one()
        for codigo in codigos:
            permiso_id = (
                await db.execute(
                    select(PermisoModel.id).where(PermisoModel.codigo == codigo)
                )
            ).scalar_one_or_none()
            if permiso_id is None:
                continue  # El DDL del PR1 los crea; si no están, no los creamos en el test
            existe = (
                await db.execute(
                    select(RolPermisoModel).where(
                        RolPermisoModel.rol_id == rol_id,
                        RolPermisoModel.permiso_id == permiso_id,
                    )
                )
            ).scalar_one_or_none()
            if existe is None:
                db.add(RolPermisoModel(rol_id=rol_id, permiso_id=permiso_id))
        await db.commit()


async def login(
    api: httpx.AsyncClient, username: str, password: str = PASSWORD_PRUEBA
) -> httpx.Response:
    return await api.post("/auth/login", json={"username": username, "password": password})


async def token_de(api: httpx.AsyncClient, username: str) -> dict:
    respuesta = await login(api, username)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def crear_categoria_directo(nombre: str) -> int:
    async with SessionLocal() as db:
        fila = CategoriaModel(nombre=nombre)
        db.add(fila)
        await db.commit()
        return fila.id


async def crear_producto_directo(
    codigo: str, nombre: str, categoria_id: int, stock: int = 0
) -> int:
    async with SessionLocal() as db:
        fila = ProductoModel(
            codigo=codigo,
            nombre=nombre,
            categoria_id=categoria_id,
            precio=10.0,
            precio_compra_actual=5.0,
            stock=stock,
            stock_minimo=5,
            activo=True,
        )
        db.add(fila)
        await db.commit()
        return fila.id


class InMemoryStorageAdapter(StoragePort):
    """Storage adapter en memoria para tests (D-T07 R2)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def subir(
        self,
        carpeta: str,
        filename: str,
        content: bytes,
        mime: str,
    ) -> StorageResult:
        self.calls.append(
            {"carpeta": carpeta, "filename": filename, "mime": mime, "size": len(content)}
        )
        return StorageResult(
            url=f"https://test/{carpeta}/{filename}",
            path=f"{carpeta}/{filename}",
            filename=filename,
            mime=mime,
            size_bytes=len(content),
            expires_at=None,
        )
