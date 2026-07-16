import asyncio
import sys

import httpx

from app.main import app

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def correr(corutina):
    async def _con_limpieza():
        try:
            return await corutina
        finally:
            pass

    return asyncio.run(_con_limpieza())


def cliente_api() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
