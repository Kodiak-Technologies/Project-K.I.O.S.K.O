import asyncio
import secrets
import sys

import httpx
from sqlalchemy import select

from app.main import app
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import RolModel, UsuarioModel
from app.modules.modulo_a_seguridad.infrastructure.adapters.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)
from app.shared.database.session import SessionLocal, engine

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PASSWORD_PRUEBA = "Prueba1234"
_hasher = BcryptPasswordHasher()
_HASH_PRUEBA = _hasher.hashear(PASSWORD_PRUEBA)


def correr(corutina):
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


async def crear_usuario_directo(username: str, rol_nombre: str, activo: bool = True) -> int:
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


async def login(api: httpx.AsyncClient, username: str, password: str = PASSWORD_PRUEBA) -> httpx.Response:
    return await api.post("/auth/login", json={"username": username, "password": password})


async def token_de(api: httpx.AsyncClient, username: str) -> dict:
    respuesta = await login(api, username)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
