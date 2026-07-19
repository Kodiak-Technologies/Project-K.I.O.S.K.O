# Caso de uso: crear un producto nuevo en el catálogo.
# El código puede venir de un escaneo (lector de barras/QR emula teclado) o escribirse a mano.
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import ConflictoError, ValidacionError


class CrearProductoUseCase:
    def __init__(self, producto_repo: ProductoRepositoryPort):
        self._productos = producto_repo

    async def ejecutar(
        self,
        codigo: str,
        nombre: str,
        categoria_id: int | None,
        precio: Decimal,
        stock_minimo: int,
        stock_inicial: int = 0,
    ) -> Producto:
        codigo = codigo.strip()
        if not codigo:
            raise ValidacionError("El código no puede estar vacío.")
        if precio <= 0:
            raise ValidacionError("El precio debe ser mayor a 0.")
        if stock_inicial < 0 or stock_minimo < 0:
            raise ValidacionError("El stock no puede ser negativo.")

        if await self._productos.buscar_por_codigo(codigo) is not None:
            raise ConflictoError(f"Ya existe un producto con el código '{codigo}'.")

        return await self._productos.crear(
            Producto(
                id=None,
                codigo=codigo,
                nombre=nombre.strip(),
                categoria_id=categoria_id,
                precio=precio,
                stock=stock_inicial,
                stock_minimo=stock_minimo,
                activo=True,
            )
        )
