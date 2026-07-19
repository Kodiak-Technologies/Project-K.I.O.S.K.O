# Adaptador: implementa ProductoStockPort leyendo/actualizando la tabla `productos`
# del Módulo B en la MISMA transacción de la venta.
#
# ¿Por qué no HTTP interno (opción recomendada por defecto en ARQUITECTURA.md §4)?
# Porque RNF-03 exige atomicidad venta+stock: si el descuento viajara por HTTP a
# otro módulo, un fallo a mitad de camino dejaría stock descontado sin venta (o al
# revés). Decisión explícita y documentada: se accede a la TABLA por SQL (nunca al
# código Python del módulo B), dentro de la misma sesión/transacción.
# El caso de uso solo conoce el puerto: cambiar esta estrategia no lo toca.
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_c_ventas.domain.entities import ProductoVendible
from app.modules.modulo_c_ventas.domain.ports.producto_stock_port import ProductoStockPort


class SqlAlchemyStockAdapter(ProductoStockPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def obtener_para_venta(self, producto_ids: list[int]) -> dict[int, ProductoVendible]:
        filas = await self._db.execute(
            text(
                "SELECT id, codigo, nombre, precio, stock, activo FROM productos "
                "WHERE id = ANY(:ids) AND deleted_at IS NULL"
            ),
            {"ids": producto_ids},
        )
        return {
            fila.id: ProductoVendible(
                id=fila.id, codigo=fila.codigo, nombre=fila.nombre,
                precio=fila.precio, stock=fila.stock, activo=fila.activo,
            )
            for fila in filas
        }

    async def descontar_stock(self, producto_id: int, cantidad: int) -> bool:
        # UPDATE condicional: atómico a nivel de fila. Si dos cajas compiten por
        # las últimas unidades, solo una gana; la otra recibe rowcount 0.
        resultado = await self._db.execute(
            text(
                "UPDATE productos SET stock = stock - :cantidad, updated_at = now() "
                "WHERE id = :id AND stock >= :cantidad AND deleted_at IS NULL"
            ),
            {"id": producto_id, "cantidad": cantidad},
        )
        return resultado.rowcount == 1

    async def reponer_stock(self, producto_id: int, cantidad: int) -> None:
        await self._db.execute(
            text(
                "UPDATE productos SET stock = stock + :cantidad, updated_at = now() "
                "WHERE id = :id"
            ),
            {"id": producto_id, "cantidad": cantidad},
        )
