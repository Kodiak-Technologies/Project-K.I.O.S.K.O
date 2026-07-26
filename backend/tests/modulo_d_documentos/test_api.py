import pytest
from tests.modulo_d_documentos.conftest import correr, cliente_api, crear_usuario_directo, token_de, auth, username_unico


# Las boletas se eliminaron en la reestructuración del Módulo D (su reemplazo
# son las notas de venta). Los tests que las ejercitaban esperaban 401 y desde
# entonces recibían 404; se reemplazan por esta comprobación de que las rutas
# efectivamente ya no existen, igual que se hizo con las mermas del Módulo B.
@pytest.mark.parametrize(
    "metodo,ruta",
    [
        ("get", "/boletas"),
        ("get", "/boletas/999"),
        ("post", "/boletas?venta_id=1"),
        ("post", "/boletas/999/subir-drive"),
    ],
)
def test_rutas_de_boletas_eliminadas(metodo, ruta):
    async def escenario():
        async with cliente_api() as api:
            respuesta = await getattr(api, metodo)(ruta)
            assert respuesta.status_code == 404

    correr(escenario())


def test_listar_notificaciones_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/notificaciones")
            assert respuesta.status_code == 401

    correr(escenario())


def test_reporte_resumen_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/reportes/resumen?desde=2026-01-01&hasta=2026-12-31")
            assert respuesta.status_code == 401

    correr(escenario())


def test_reporte_exportar_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/reportes/exportar?desde=2026-01-01&hasta=2026-12-31")
            assert respuesta.status_code == 401

    correr(escenario())


def test_respaldos_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/respaldos")
            assert respuesta.status_code == 401

    correr(escenario())


def test_notificacion_marcar_leida_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.post("/notificaciones/999/leida")
            assert respuesta.status_code == 401

    correr(escenario())


def test_health():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/health")
            assert respuesta.status_code == 200
            assert respuesta.json()["status"] == "ok"

    correr(escenario())


def test_crear_respaldo_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.post("/respaldos")
            assert respuesta.status_code == 401

    correr(escenario())


def test_descargar_respaldo_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/respaldos/999/descargar")
            assert respuesta.status_code == 401

    correr(escenario())


def test_drive_auth_url_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/drive/auth-url")
            assert respuesta.status_code == 200
            data = respuesta.json()
            assert "auth_url" in data
            assert "accounts.google.com" in data["auth_url"]

    correr(escenario())


def test_drive_status_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/drive/status")
            assert respuesta.status_code == 200
            data = respuesta.json()
            assert "autorizado" in data

    correr(escenario())


def test_drive_callback_sin_code():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/drive/callback")
            # `code` es opcional a propósito: acá aterriza el redirect de
            # Google, así que la falta de código se contesta con un mensaje
            # legible y no con un 422 que el usuario vería como error crudo.
            assert respuesta.status_code == 200
            assert "error" in respuesta.json()

    correr(escenario())


def test_crear_notificacion_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.post(
                "/notificaciones",
                json={"tipo": "SISTEMA", "titulo": "Test", "mensaje": "Prueba"},
            )
            assert respuesta.status_code == 401

    correr(escenario())


def test_config_notificaciones_get_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/notificaciones/config")
            assert respuesta.status_code == 401

    correr(escenario())


def test_config_notificaciones_put_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.put(
                "/notificaciones/config",
                json={"nivel_detalle": "MEDIO"},
            )
            assert respuesta.status_code == 401

    correr(escenario())


def test_notificaciones_con_auth():
    async def escenario():
        username = username_unico("admin_notif")
        await crear_usuario_directo(username, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.get("/notificaciones", headers=auth(tokens["access_token"]))
            assert respuesta.status_code == 200
            # Devuelve el envoltorio paginado estándar desde la 6ª pasada,
            # no una lista plana.
            data = respuesta.json()
            assert isinstance(data["items"], list)
            assert {"total", "page", "page_size", "total_pages"} <= data.keys()

    correr(escenario())


def test_reporte_resumen_con_auth():
    async def escenario():
        username = username_unico("admin_resumen")
        await crear_usuario_directo(username, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.get(
                "/reportes/resumen?desde=2026-01-01&hasta=2026-12-31",
                headers=auth(tokens["access_token"]),
            )
            assert respuesta.status_code == 200
            data = respuesta.json()
            assert "total_vendido" in data
            assert "total_egresos" in data
            assert "metodos_pago" in data

    correr(escenario())


def test_reporte_mas_vendidos_con_auth():
    async def escenario():
        username = username_unico("admin_top")
        await crear_usuario_directo(username, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.get(
                "/reportes/mas-vendidos?desde=2026-01-01&hasta=2026-12-31",
                headers=auth(tokens["access_token"]),
            )
            assert respuesta.status_code == 200
            assert isinstance(respuesta.json(), list)

    correr(escenario())


def test_config_notificaciones_get_con_auth():
    async def escenario():
        username = username_unico("admin_cfg")
        await crear_usuario_directo(username, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.get("/notificaciones/config", headers=auth(tokens["access_token"]))
            assert respuesta.status_code == 200
            # La config quedó reducida a `nivel_detalle`: los canales
            # (telegram/correo) salieron del schema en la reestructuración.
            data = respuesta.json()
            assert "nivel_detalle" in data

    correr(escenario())


def test_config_notificaciones_put_con_auth():
    async def escenario():
        username = username_unico("admin_cfgput")
        await crear_usuario_directo(username, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.put(
                "/notificaciones/config",
                json={"nivel_detalle": "MEDIO"},
                headers=auth(tokens["access_token"]),
            )
            assert respuesta.status_code == 200
            assert respuesta.json()["nivel_detalle"] == "MEDIO"

    correr(escenario())


def test_respaldos_con_auth():
    async def escenario():
        username = username_unico("admin_resp")
        await crear_usuario_directo(username, "ADMIN")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.get("/respaldos", headers=auth(tokens["access_token"]))
            assert respuesta.status_code == 200
            # Envoltorio paginado estándar desde la 6ª pasada.
            data = respuesta.json()
            assert isinstance(data["items"], list)
            assert {"total", "page", "page_size", "total_pages"} <= data.keys()

    correr(escenario())


def test_notificaciones_config_put_no_admin():
    async def escenario():
        username = username_unico("cajero_cfg")
        await crear_usuario_directo(username, "CAJERO")
        async with cliente_api() as api:
            tokens = await token_de(api, username)
            respuesta = await api.put(
                "/notificaciones/config",
                json={
                    "canal_telegram_activo": True,
                    "canal_correo_activo": False,
                    "nivel_detalle": "MEDIO",
                },
                headers=auth(tokens["access_token"]),
            )
            assert respuesta.status_code == 403

    correr(escenario())
