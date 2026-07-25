# Caso de uso: listar historial de precios de un producto (HU-B11 segunda parte, REQ-11-H).
from app.modules.modulo_b_inventario.domain.entities import HistorialPrecio
from app.modules.modulo_b_inventario.domain.ports.historial_precio_repository_port import (
    HistorialPrecioRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


class ListarHistorialPreciosUseCase:
    def __init__(self, historial_repo: HistorialPrecioRepositoryPort):
        self._historial = historial_repo

    async def ejecutar(
        self,
        producto_id: int,
        tipo: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[HistorialPrecio], int, int, int, int]:
        if tipo is not None and tipo not in ("venta", "compra"):
            raise ValidacionError("tipo debe ser 'venta' o 'compra'.")
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        items, total = await self._historial.listar_por_producto(
            producto_id, tipo=tipo, page=page, page_size=page_size
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return items, total, page, page_size, total_pages
