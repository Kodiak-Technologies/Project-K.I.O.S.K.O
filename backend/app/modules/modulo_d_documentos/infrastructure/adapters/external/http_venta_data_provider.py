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


class HttpVentaDataProvider:
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

    async def obtener_venta(self, venta_id: int) -> dict | None:
        try:
            client = await self._get_client()
            resp = await client.get("/ventas", headers=self._headers)
            if resp.status_code != 200:
                return None
            for v in resp.json():
                if v["id"] == venta_id:
                    return {
                        "id": v["id"],
                        "total": v["total"],
                        "metodo_pago": v["metodo_pago"],
                        "estado": v["estado"],
                        "vendedor": v["vendedor"],
                        "fecha": v.get("vendida_en") or v.get("created_at"),
                        "vuelto": v.get("vuelto", 0),
                        "pagos": v.get("pagos", []),
                    }
            return None
        except Exception:
            return None

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        try:
            params: dict = {}
            if desde:
                params["desde"] = desde
            if hasta:
                params["hasta"] = hasta
            client = await self._get_client()
            resp = await client.get("/ventas", params=params, headers=self._headers)
            if resp.status_code != 200:
                return []
            return [
                {
                    "id": v["id"],
                    "total": v["total"],
                    "metodo_pago": v["metodo_pago"],
                    "estado": v["estado"],
                    "vendedor": v["vendedor"],
                    "fecha": v.get("vendida_en") or v.get("created_at"),
                    "vuelto": v.get("vuelto", 0),
                    "pagos": v.get("pagos", []),
                }
                for v in resp.json()
            ]
        except Exception:
            return []

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        try:
            client = await self._get_client()
            resp = await client.get("/ventas", headers=self._headers)
            if resp.status_code != 200:
                return []
            for v in resp.json():
                if v["id"] == venta_id:
                    return [
                        {
                            "producto_id": item["producto_id"],
                            "nombre": item["nombre"],
                            "precio_unitario": item["precio_unitario"],
                            "cantidad": item["cantidad"],
                        }
                        for item in v.get("items", [])
                    ]
            return []
        except Exception:
            return []

    async def obtener_pagos_venta(self, venta_id: int) -> list[dict]:
        try:
            client = await self._get_client()
            resp = await client.get("/ventas", headers=self._headers)
            if resp.status_code != 200:
                return []
            for v in resp.json():
                if v["id"] == venta_id:
                    return v.get("pagos", [])
            return []
        except Exception:
            return []
