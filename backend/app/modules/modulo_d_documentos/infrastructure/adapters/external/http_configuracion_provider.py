import httpx

from app.main import app


class HttpConfiguracionProvider:
    def __init__(self):
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://internal",
        )

    async def obtener(self) -> dict:
        try:
            resp = await self._client.get(
                "/configuracion",
                headers={"Authorization": "Bearer internal"},
            )
            if resp.status_code != 200:
                return {"nombre_negocio": "Mi Tienda", "logo_url": ""}
            data = resp.json()
            return {
                "nombre_negocio": data.get("nombre_negocio", "Mi Tienda"),
                "logo_url": data.get("logo_url", ""),
            }
        except Exception:
            return {"nombre_negocio": "Mi Tienda", "logo_url": ""}
