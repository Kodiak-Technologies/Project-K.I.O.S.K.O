# Caso de uso: listar productos a reponer (HU-B13, REQ-13).
# Filtra stock <= stock_minimo, ordenado por faltante DESC.
from dataclasses import dataclass
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


@dataclass
class PorReponerItem:
    producto: Producto
    faltante: int


class ListarProductosPorReponerUseCase:
    def __init__(self, producto_repo: ProductoRepositoryPort):
        self._productos = producto_repo

    async def ejecutar(
        self,
        categoria_id: int | None = None,
        solo_no_notificadas: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PorReponerItem], int, int, int, int]:
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        items = await self._productos.find_bajo_minimo(
            categoria_id=categoria_id,
            solo_no_notificadas=solo_no_notificadas,
            page=page,
            page_size=page_size,
        )
        result = [
            PorReponerItem(producto=p, faltante=p.stock_minimo - p.stock)
            for p in items
        ]
        if solo_no_notificadas:
            # El count por `listar_paginado` no distingue alertas ya avisadas;
            # con este filtro el total es el de la página traída.
            total = len(result)
        else:
            # Necesitamos el total exacto; el port find_bajo_minimo no lo devuelve.
            # Hacemos un count aparte usando listar_paginado con solo_bajo_minimo.
            _, total = await self._productos.listar_paginado(
                categoria_id=categoria_id,
                solo_bajo_minimo=True,
                activo=True,
                page=1,
                page_size=1,
            )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return result, total, page, page_size, total_pages

    async def marcar_notificadas(self, producto_ids: list[int]) -> int:
        """HU-B13: 'alerta única por producto hasta su reposición'."""
        return await self._productos.marcar_alertas_notificadas(producto_ids)
