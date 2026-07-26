# Caso de uso: listar movimientos de inventario con filtros.
from datetime import datetime

from app.modules.modulo_b_inventario.domain.entities import MovimientoInventario
from app.modules.modulo_b_inventario.domain.ports.movimiento_inventario_repository_port import (
    MovimientoInventarioRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


class ListarMovimientosInventarioUseCase:
    def __init__(self, movimiento_repo: MovimientoInventarioRepositoryPort):
        self._movimientos = movimiento_repo

    async def ejecutar(
        self,
        *,
        producto_id: int | None = None,
        tipo: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[MovimientoInventario], int, int, int, int]:
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        if tipo is not None and tipo not in (
            "ingreso",
            "merma",
            "ajuste",
            "venta",
            "devolucion",
        ):
            raise ValidacionError(
                "tipo debe ser uno de: ingreso, merma, ajuste, venta, devolucion."
            )
        items, total = await self._movimientos.listar_paginado(
            producto_id=producto_id,
            tipo=tipo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            page=page,
            page_size=page_size,
            cursor=cursor,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return items, total, page, page_size, total_pages
