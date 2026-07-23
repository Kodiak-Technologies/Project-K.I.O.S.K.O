import httpx

from app.main import app


class HttpVentaDataProvider:
    def __init__(self):
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://internal",
        )

    async def obtener_venta(self, venta_id: int) -> dict | None:
        try:
            resp = await self._client.get(
                "/ventas",
                headers={"Authorization": "Bearer internal"},
            )
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
            resp = await self._client.get(
                "/ventas",
                params=params,
                headers={"Authorization": "Bearer internal"},
            )
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
                }
                for v in resp.json()
            ]
        except Exception:
            return []

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        try:
            resp = await self._client.get(
                "/ventas",
                headers={"Authorization": "Bearer internal"},
            )
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
