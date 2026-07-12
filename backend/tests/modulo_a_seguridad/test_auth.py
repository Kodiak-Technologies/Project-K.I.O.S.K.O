# Tests de autenticación: login correcto/incorrecto, bloqueo tras 3 intentos y refresh token.
from tests.modulo_a_seguridad.conftest import (
    PASSWORD_PRUEBA,
    cliente_api,
    correr,
    crear_usuario_directo,
    login,
    token_de,
    username_unico,
)


def test_login_correcto():
    async def escenario():
        username = username_unico("cajero")
        await crear_usuario_directo(username, "CAJERO")
        async with cliente_api() as api:
            respuesta = await login(api, username)
            assert respuesta.status_code == 200
            cuerpo = respuesta.json()
            assert cuerpo["access_token"]
            assert cuerpo["refresh_token"]
            assert cuerpo["usuario"]["username"] == username
            assert cuerpo["usuario"]["rol"] == "CAJERO"

    correr(escenario())


def test_login_incorrecto_mensaje_generico():
    async def escenario():
        username = username_unico("cajero")
        await crear_usuario_directo(username, "CAJERO")
        async with cliente_api() as api:
            respuesta = await login(api, username, "ContraseñaMala99")
            assert respuesta.status_code == 401
            # Mensaje genérico: no revela si falló el usuario o la contraseña.
            assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos."

            # Usuario inexistente: exactamente el mismo mensaje y código.
            respuesta2 = await login(api, "no_existe_xyz", "ContraseñaMala99")
            assert respuesta2.status_code == 401
            assert respuesta2.json()["detail"] == respuesta.json()["detail"]

    correr(escenario())


def test_bloqueo_tras_tres_intentos_fallidos():
    async def escenario():
        username = username_unico("cajero")
        await crear_usuario_directo(username, "CAJERO")
        async with cliente_api() as api:
            for _ in range(3):
                respuesta = await login(api, username, "ContraseñaMala99")
                assert respuesta.status_code == 401

            # Al 4to intento la cuenta ya está bloqueada, INCLUSO con la contraseña correcta.
            respuesta = await login(api, username, PASSWORD_PRUEBA)
            assert respuesta.status_code == 423
            assert "bloqueada" in respuesta.json()["detail"].lower()

    correr(escenario())


def test_refresh_token_rota_y_revoca_el_anterior():
    async def escenario():
        username = username_unico("cajero")
        await crear_usuario_directo(username, "CAJERO")
        async with cliente_api() as api:
            tokens = await token_de(api, username)

            # El refresh entrega tokens nuevos.
            respuesta = await api.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
            assert respuesta.status_code == 200
            nuevos = respuesta.json()
            assert nuevos["access_token"]
            assert nuevos["refresh_token"] != tokens["refresh_token"]

            # El refresh token viejo quedó revocado (rotación).
            reuso = await api.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
            assert reuso.status_code == 401

    correr(escenario())


def test_me_devuelve_usuario_autenticado():
    async def escenario():
        username = username_unico("cajero")
        await crear_usuario_directo(username, "CAJERO")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.get(
                "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            assert respuesta.status_code == 200
            assert respuesta.json()["username"] == username

            sin_token = await api.get("/auth/me")
            assert sin_token.status_code == 401

    correr(escenario())
