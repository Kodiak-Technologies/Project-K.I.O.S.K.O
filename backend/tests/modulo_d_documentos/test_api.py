import pytest
from tests.modulo_d_documentos.conftest import correr, cliente_api


def test_listar_boletas_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/boletas")
            assert respuesta.status_code == 401

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


def test_boleta_por_id_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.get("/boletas/999")
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


def test_subir_boleta_drive_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.post("/boletas/999/subir-drive")
            assert respuesta.status_code == 401

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


def test_crear_boleta_sin_auth():
    async def escenario():
        async with cliente_api() as api:
            respuesta = await api.post("/boletas?venta_id=1")
            assert respuesta.status_code == 401

    correr(escenario())
