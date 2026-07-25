# Caso de uso: buscar productos por nombre o categoría (HU-B04, REQ-04).
# `ILIKE %nombre%`, excluye inactivos/soft-deleted, limita a 50 resultados (REQ-04-03).
from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


class BuscarProductoPorNombreUseCase:
    MAX_RESULTADOS = 50

    def __init__(self, producto_repo: ProductoRepositoryPort):
        self._productos = producto_repo

    async def ejecutar(
        self,
        nombre: str,
        categoria_id: int | None = None,
        limit: int = 20,
    ) -> list[Producto]:
        nombre = (nombre or "").strip()
        if len(nombre) < 2:
            raise ValidacionError("El nombre debe tener al menos 2 caracteres.")
        limit = min(limit, self.MAX_RESULTADOS)
        # Reusamos listar_paginado con search
        items, _ = await self._productos.listar_paginado(
            search=nombre,
            categoria_id=categoria_id,
            activo=True,
            page=1,
            page_size=limit,
        )
        return items
