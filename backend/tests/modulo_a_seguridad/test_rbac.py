# Tests de RBAC: un CAJERO recibe 403 en acciones de ADMIN aunque llame la API directamente.
from tests.modulo_a_seguridad.conftest import (
    auth,
    cliente_api,
    correr,
    crear_usuario_directo,
    token_de,
    username_unico,
)


def test_cajero_recibe_403_en_endpoints_de_admin():
    async def escenario():
        username = username_unico("cajero")
        await crear_usuario_directo(username, "CAJERO")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            headers = auth(tokens["access_token"])

            # Gestión de usuarios: prohibida.
            assert (await api.get("/usuarios", headers=headers)).status_code == 403
            crear = await api.post(
                "/usuarios",
                headers=headers,
                json={"username": "hackeo1", "nombre": "X", "password": "Password1", "rol_id": 1},
            )
            assert crear.status_code == 403

            # Bitácora: prohibida.
            assert (await api.get("/bitacora", headers=headers)).status_code == 403

            # Configuración: leer sí, editar no.
            assert (await api.get("/configuracion", headers=headers)).status_code == 200
            editar = await api.patch(
                "/configuracion", headers=headers, json={"nombre_negocio": "Hackeada"}
            )
            assert editar.status_code == 403

            # Roles/permisos: prohibidos.
            assert (await api.get("/roles", headers=headers)).status_code == 403

    correr(escenario())


def test_admin_si_puede_gestionar_usuarios():
    async def escenario():
        username = username_unico("admin")
        await crear_usuario_directo(username, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.get("/usuarios", headers=auth(tokens["access_token"]))
            assert respuesta.status_code == 200
            assert isinstance(respuesta.json(), list)

    correr(escenario())
