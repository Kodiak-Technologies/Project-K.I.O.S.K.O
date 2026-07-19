# Caso de uso: actualizar datos de un producto existente (solo ADMIN, el router lo garantiza).
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError, ValidacionError


class ActualizarProductoUseCase:
    def __init__(self, producto_repo: ProductoRepositoryPort):
        self._productos = producto_repo

    async def ejecutar(self, producto_id: int, cambios: dict) -> Producto:
        actual = await self._productos.buscar_por_id(producto_id)
        if actual is None:
            raise NoEncontradoError("Producto no encontrado.")

        precio = cambios.get("precio")
        if precio is not None and Decimal(str(precio)) <= 0:
            raise ValidacionError("El precio debe ser mayor a 0.")

        codigo = cambios.get("codigo")
        if codigo is not None:
            existente = await self._productos.buscar_por_codigo(codigo.strip())
            if existente is not None and existente.id != producto_id:
                raise ConflictoError(f"Ya existe un producto con el código '{codigo}'.")

        return await self._productos.actualizar(producto_id, cambios)
