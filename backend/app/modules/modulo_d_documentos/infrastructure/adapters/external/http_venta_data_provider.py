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

    # `GET /ventas` ahora responde paginado: `{items, total, page, ...}`.
    # Estos helpers aíslan ese detalle del resto del adaptador.
    TAMANO_PAGINA = 100

    @staticmethod
    def _resumen(v: dict) -> dict:
        return {
            "id": v["id"],
            "total": v["total"],
            "metodo_pago": v["metodo_pago"],
            "estado": v["estado"],
            "vendedor": v["vendedor"],
            "fecha": v.get("vendida_en") or v.get("created_at"),
            "vuelto": v.get("vuelto", 0),
            "pagos": v.get("pagos", []),
            "items": v.get("items", []),
        }

    async def _todas_las_ventas(self, params: dict | None = None) -> list[dict]:
        """Recorre las páginas hasta juntar todo el rango pedido."""
        client = await self._get_client()
        ventas: list[dict] = []
        page = 1
        while True:
            consulta = dict(params or {})
            consulta.update({"page": page, "page_size": self.TAMANO_PAGINA})
            resp = await client.get("/ventas", params=consulta, headers=self._headers)
            if resp.status_code != 200:
                break
            cuerpo = resp.json()
            ventas.extend(cuerpo.get("items", []))
            if page >= cuerpo.get("total_pages", 1) or not cuerpo.get("items"):
                break
            page += 1
        return ventas

    async def _venta_cruda(self, venta_id: int) -> dict | None:
        """Una sola venta por su id (sin recorrer el histórico entero)."""
        try:
            client = await self._get_client()
            resp = await client.get(f"/ventas/{venta_id}", headers=self._headers)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    async def obtener_venta(self, venta_id: int) -> dict | None:
        v = await self._venta_cruda(venta_id)
        return self._resumen(v) if v else None

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        try:
            params: dict = {}
            if desde:
                params["desde"] = desde
            if hasta:
                params["hasta"] = hasta
            return [self._resumen(v) for v in await self._todas_las_ventas(params)]
        except Exception:
            return []

    async def listar_ventas_paginado(
        self,
        desde: str | None = None,
        hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Una sola llamada a `/ventas`: no recorre el histórico entero."""
        try:
            params: dict = {"page": page, "page_size": page_size}
            if desde:
                params["desde"] = desde
            if hasta:
                params["hasta"] = hasta
            client = await self._get_client()
            resp = await client.get("/ventas", params=params, headers=self._headers)
            if resp.status_code != 200:
                return [], 0
            cuerpo = resp.json()
            return (
                [self._resumen(v) for v in cuerpo.get("items", [])],
                cuerpo.get("total", 0),
            )
        except Exception:
            return [], 0

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        v = await self._venta_cruda(venta_id)
        if v is None:
            return []
        return [
            {
                "producto_id": item["producto_id"],
                "nombre": item["nombre"],
                "precio_unitario": item["precio_unitario"],
                "cantidad": item["cantidad"],
                # Lo devuelto no se vendió: el reporte lo descuenta.
                "cantidad_devuelta": item.get("cantidad_devuelta", 0),
            }
            for item in v.get("items", [])
        ]

    async def obtener_pagos_venta(self, venta_id: int) -> list[dict]:
        v = await self._venta_cruda(venta_id)
        return v.get("pagos", []) if v else []
