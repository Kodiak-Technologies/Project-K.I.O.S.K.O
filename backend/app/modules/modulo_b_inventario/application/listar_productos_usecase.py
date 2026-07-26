# Caso de uso: listar productos paginado con filtros (HU-B09, REQ-09).
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


class ListarProductosUseCase:
    def __init__(self, producto_repo: ProductoRepositoryPort):
        self._productos = producto_repo

    async def ejecutar(
        self,
        *,
        search: str | None = None,
        categoria_id: int | None = None,
        solo_con_stock: bool = False,
        solo_bajo_minimo: bool = False,
        sin_stock: bool = False,
        precio_min: Decimal | None = None,
        precio_max: Decimal | None = None,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Producto], int, int, int, int]:
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        if precio_min is not None and precio_min < 0:
            raise ValidacionError("precio_min no puede ser negativo.")
        if precio_min is not None and precio_max is not None and precio_min > precio_max:
            raise ValidacionError("precio_min no puede ser mayor que precio_max.")
        items, total = await self._productos.listar_paginado(
            search=search,
            categoria_id=categoria_id,
            solo_con_stock=solo_con_stock,
            solo_bajo_minimo=solo_bajo_minimo,
            sin_stock=sin_stock,
            precio_min=precio_min,
            precio_max=precio_max,
            activo=activo,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return items, total, page, page_size, total_pages
