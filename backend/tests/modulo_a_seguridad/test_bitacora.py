# Tests de la bitácora: registra los eventos y es INMUTABLE (ni UPDATE ni DELETE, ni siquiera vía SQL).
import pytest
from sqlalchemy import text

from app.shared.database.session import SessionLocal
from tests.modulo_a_seguridad.conftest import (
    auth,
    cliente_api,
    correr,
    crear_usuario_directo,
    login,
    token_de,
    username_unico,
)


def test_bitacora_registra_login_exitoso_y_fallido():
    async def escenario():
        username_admin = username_unico("admin")
        username_cajero = username_unico("cajero")
        await crear_usuario_directo(username_admin, "ADMIN")
        cajero_id = await crear_usuario_directo(username_cajero, "CAJERO")

        async with cliente_api() as api:
            await login(api, username_cajero, "ContraseñaMala99")  # fallido
            await login(api, username_cajero)  # exitoso

            tokens = await token_de(api, username_admin)
            respuesta = await api.get(
                "/bitacora",
                headers=auth(tokens["access_token"]),
                params={"usuario_id": cajero_id, "entidad": "usuarios"},
            )
            assert respuesta.status_code == 200
            acciones = [r["accion"] for r in respuesta.json()["registros"]]
            assert "login_fallido" in acciones
            assert "login_exitoso" in acciones

    correr(escenario())


def test_bitacora_filtra_por_accion():
    async def escenario():
        username_admin = username_unico("admin")
        await crear_usuario_directo(username_admin, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username_admin)
            respuesta = await api.get(
                "/bitacora",
                headers=auth(tokens["access_token"]),
                params={"accion": "login_exitoso"},
            )
            assert respuesta.status_code == 200
            cuerpo = respuesta.json()
            assert cuerpo["total"] >= 1
            assert all(r["accion"] == "login_exitoso" for r in cuerpo["registros"])

    correr(escenario())


def test_bitacora_es_inmutable_a_nivel_de_base_de_datos():
    async def escenario():
        # El trigger de Postgres debe rechazar UPDATE y DELETE aunque se intenten por SQL directo.
        async with SessionLocal() as db:
            with pytest.raises(Exception, match="inmutable"):
                await db.execute(text("UPDATE bitacora_auditoria SET accion = 'adulterada' WHERE id > 0"))
            await db.rollback()
            with pytest.raises(Exception, match="inmutable"):
                await db.execute(text("DELETE FROM bitacora_auditoria WHERE id > 0"))
            await db.rollback()

    correr(escenario())


def test_no_existen_endpoints_de_modificacion_de_bitacora():
    async def escenario():
        username_admin = username_unico("admin")
        await crear_usuario_directo(username_admin, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username_admin)
            headers = auth(tokens["access_token"])
            # Ni siquiera el ADMIN tiene rutas para modificar o borrar la bitácora.
            assert (await api.put("/bitacora", headers=headers, json={})).status_code == 405
            assert (await api.patch("/bitacora", headers=headers, json={})).status_code == 405
            assert (await api.delete("/bitacora", headers=headers)).status_code == 405
            # Y tampoco existen rutas por id.
            assert (await api.delete("/bitacora/1", headers=headers)).status_code in (404, 405)

    correr(escenario())
