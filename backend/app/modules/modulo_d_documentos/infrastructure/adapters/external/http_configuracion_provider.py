from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt

from app.shared.config.settings import settings


def _generar_token_sistema() -> str:
    ahora = datetime.now(timezone.utc)
    claims = {
        "sub": "1",
        "username": "system",
        "rol": "ADMIN",
        "type": "access",
        "iat": ahora,
        "exp": ahora + timedelta(hours=24),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)


TOKEN_SISTEMA = _generar_token_sistema()


class HttpConfiguracionProvider:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._headers = {"Authorization": f"Bearer {TOKEN_SISTEMA}"}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            from app.main import app
            self._client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://internal",
            )
        return self._client

    async def obtener(self) -> dict:
        try:
            client = await self._get_client()
            resp = await client.get("/configuracion", headers=self._headers)
            if resp.status_code != 200:
                return {"nombre_negocio": "Mi Tienda", "logo_url": ""}
            data = resp.json()
            return {
                "nombre_negocio": data.get("nombre_negocio", "Mi Tienda"),
                "logo_url": data.get("logo_url", ""),
            }
        except Exception:
            return {"nombre_negocio": "Mi Tienda", "logo_url": ""}
