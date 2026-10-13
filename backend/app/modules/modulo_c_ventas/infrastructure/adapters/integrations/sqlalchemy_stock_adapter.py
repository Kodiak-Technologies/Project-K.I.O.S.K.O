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
                "SELECT id, codigo, nombre, precio, stock, stock_minimo, activo "
                "FROM productos WHERE id = ANY(:ids) AND deleted_at IS NULL"
            ),
            {"ids": producto_ids},
        )
        return {
            fila.id: ProductoVendible(
                id=fila.id, codigo=fila.codigo, nombre=fila.nombre,
                precio=fila.precio, stock=fila.stock, stock_minimo=fila.stock_minimo,
                activo=fila.activo,
            )
            for fila in filas
        }

    async def descontar_stock(
        self,
        cantidades: dict[int, int],
        usuario_id: int | None = None,
        usuario_nombre: str = "",
    ) -> set[int]:
        # Una sola consulta para todo el carrito (antes eran 2 por producto: el
        # UPDATE y el asiento). El UPDATE sigue siendo condicional por fila: si
        # dos cajas compiten por las últimas unidades, solo una gana; a la otra
        # ese producto no le aparece en RETURNING.
        # D-07: `movimientos_inventario` es la bitácora de TODA variación de
        # stock; el asiento va en la misma sentencia. Sin `usuario_id` no se
        # cumple el NOT NULL de `registrado_por` y se omite el asiento en vez
        # de romper la venta.
        ids = list(cantidades)
        parametros = {"ids": ids, "cantidades": [cantidades[i] for i in ids]}
        asiento = " "
        if usuario_id is not None:
            asiento = (
                ", asientos AS ("
                "  INSERT INTO movimientos_inventario "
                "  (producto_id, cantidad, tipo, motivo, registrado_por, registrado_por_nombre) "
                "  SELECT id, -cantidad, 'venta', NULL, "
                "         CAST(:usuario_id AS bigint), CAST(:usuario_nombre AS varchar) "
                "  FROM descontados"
                ") "
            )
            parametros |= {"usuario_id": usuario_id, "usuario_nombre": usuario_nombre or ""}
        filas = await self._db.execute(
            text(
                "WITH pedido AS ("
                "  SELECT * FROM unnest(CAST(:ids AS bigint[]), CAST(:cantidades AS integer[])) "
                "  AS p(id, cantidad)"
                "), descontados AS ("
                "  UPDATE productos AS pr "
                "  SET stock = pr.stock - p.cantidad, updated_at = now() "
                "  FROM pedido AS p "
                "  WHERE pr.id = p.id AND pr.stock >= p.cantidad AND pr.deleted_at IS NULL "
                "  RETURNING pr.id, p.cantidad"
                ")" + asiento + "SELECT id FROM descontados"
            ),
            parametros,
        )
        return set(cantidades) - {fila.id for fila in filas}

    async def reponer_stock(
        self,
        producto_id: int,
        cantidad: int,
        usuario_id: int | None = None,
        usuario_nombre: str = "",
        motivo: str | None = None,
    ) -> None:
        await self._db.execute(
            text(
                "UPDATE productos SET stock = stock + :cantidad, updated_at = now(), "
                "alerta_stock_notificada = CASE WHEN stock + :cantidad > stock_minimo "
                "THEN FALSE ELSE alerta_stock_notificada END "
                "WHERE id = :id"
            ),
            {"id": producto_id, "cantidad": cantidad},
        )
        await self._registrar_movimiento(
            producto_id, cantidad, "devolucion", motivo, usuario_id, usuario_nombre
        )

    async def marcar_alerta_stock(self, producto_id: int) -> bool:
        """Marca la alerta de stock mínimo; True solo la primera vez (RF-24).

        UPDATE condicional: si dos ventas dejan el producto bajo mínimo a la vez,
        sale un único aviso.
        """
        resultado = await self._db.execute(
            text(
                "UPDATE productos SET alerta_stock_notificada = TRUE "
                "WHERE id = :id AND alerta_stock_notificada = FALSE"
            ),
            {"id": producto_id},
        )
        return resultado.rowcount == 1

    async def _registrar_movimiento(
        self,
        producto_id: int,
        cantidad: int,
        tipo: str,
        motivo: str | None,
        usuario_id: int | None,
        usuario_nombre: str,
    ) -> None:
        """INSERT en la bitácora del Módulo B (misma transacción, por SQL).

        Sin `usuario_id` no se puede cumplir el NOT NULL de `registrado_por`;
        en ese caso se omite el asiento en vez de romper la venta.
        """
        if usuario_id is None:
            return
        await self._db.execute(
            text(
                "INSERT INTO movimientos_inventario "
                "(producto_id, cantidad, tipo, motivo, registrado_por, registrado_por_nombre) "
                "VALUES (:producto_id, :cantidad, :tipo, :motivo, :usuario_id, :usuario_nombre)"
            ),
            {
                "producto_id": producto_id,
                "cantidad": cantidad,
                "tipo": tipo,
                "motivo": motivo,
                "usuario_id": usuario_id,
                "usuario_nombre": usuario_nombre or "",
            },
        )
