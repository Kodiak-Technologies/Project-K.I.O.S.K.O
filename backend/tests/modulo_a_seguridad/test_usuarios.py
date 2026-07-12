# Tests de gestión de usuarios: borrado lógico (nunca físico) y desactivación sin perder historial.
from sqlalchemy import select

from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import UsuarioModel
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


def test_eliminar_usuario_es_borrado_logico():
    async def escenario():
        username_admin = username_unico("admin")
        username_victima = username_unico("cajero")
        await crear_usuario_directo(username_admin, "ADMIN")
        victima_id = await crear_usuario_directo(username_victima, "CAJERO")

        async with cliente_api() as api:
            tokens = await token_de(api, username_admin)
            headers = auth(tokens["access_token"])

            respuesta = await api.delete(f"/usuarios/{victima_id}", headers=headers)
            assert respuesta.status_code == 204

            # La API ya no lo muestra...
            assert (await api.get(f"/usuarios/{victima_id}", headers=headers)).status_code == 404
            # ...y no puede loguearse...
            assert (await login(api, username_victima)).status_code == 401

        # ...PERO la fila sigue existiendo en la BD (borrado lógico: historial trazable).
        async with SessionLocal() as db:
            fila = (
                await db.execute(select(UsuarioModel).where(UsuarioModel.id == victima_id))
            ).scalar_one()
            assert fila.deleted_at is not None
            assert fila.deleted_by is not None

    correr(escenario())


def test_desactivar_impide_login_pero_conserva_al_usuario():
    async def escenario():
        username_admin = username_unico("admin")
        username_cajero = username_unico("cajero")
        await crear_usuario_directo(username_admin, "ADMIN")
        cajero_id = await crear_usuario_directo(username_cajero, "CAJERO")

        async with cliente_api() as api:
            tokens = await token_de(api, username_admin)
            headers = auth(tokens["access_token"])

            respuesta = await api.patch(
                f"/usuarios/{cajero_id}/estado", headers=headers, json={"activo": False}
            )
            assert respuesta.status_code == 200
            assert respuesta.json()["activo"] is False

            # No puede entrar (mensaje genérico), pero sigue listado para el ADMIN.
            assert (await login(api, username_cajero)).status_code == 401
            listado = (await api.get("/usuarios", headers=headers)).json()
            assert any(u["id"] == cajero_id for u in listado)

            # Reactivar lo deja entrar de nuevo.
            await api.patch(f"/usuarios/{cajero_id}/estado", headers=headers, json={"activo": True})
            assert (await login(api, username_cajero)).status_code == 200

    correr(escenario())


def test_admin_crea_usuario_y_este_puede_loguearse():
    async def escenario():
        username_admin = username_unico("admin")
        await crear_usuario_directo(username_admin, "ADMIN")
        nuevo_username = username_unico("nuevo")

        async with cliente_api() as api:
            tokens = await token_de(api, username_admin)
            respuesta = await api.post(
                "/usuarios",
                headers=auth(tokens["access_token"]),
                json={
                    "username": nuevo_username,
                    "nombre": "Vendedor Nuevo",
                    "password": "Inicial1234",
                    "rol_id": 2,  # CAJERO (según seed)
                    "forzar_cambio_password": True,
                },
            )
            assert respuesta.status_code == 201, respuesta.text
            assert respuesta.json()["debe_cambiar_password"] is True

            ingreso = await login(api, nuevo_username, "Inicial1234")
            assert ingreso.status_code == 200
            assert ingreso.json()["usuario"]["debe_cambiar_password"] is True

    correr(escenario())
