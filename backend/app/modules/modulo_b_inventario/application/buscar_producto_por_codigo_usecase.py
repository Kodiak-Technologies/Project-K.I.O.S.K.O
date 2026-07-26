# Caso de uso: buscar un producto por código (HU-B02, REQ-02).
# < 100 ms esperado (índice UNIQUE en productos.codigo).
from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import NoEncontradoError


class BuscarProductoPorCodigoUseCase:
    def __init__(self, producto_repo: ProductoRepositoryPort):
        self._productos = producto_repo

    async def ejecutar(self, codigo: str) -> Producto:
        if not codigo or not codigo.strip():
            raise NoEncontradoError("Producto no encontrado.")
        p = await self._productos.buscar_por_codigo(codigo.strip())
        if p is None or not p.activo or p.deleted_at is not None:
            # Inactivo o soft-deleted: 404 (REQ-02, R2)
            raise NoEncontradoError("Producto no encontrado.")
        return p
