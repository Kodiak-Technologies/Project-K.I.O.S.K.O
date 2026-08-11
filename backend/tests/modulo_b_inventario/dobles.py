"""Dobles en memoria de los puertos del Módulo B.

Siguen la firma real de cada puerto. El de productos simula además el UPDATE
atómico de stock (`incrementar_stock_atomic`), que es donde vive la regla de
que el stock nunca queda negativo.
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.modulo_b_inventario.domain.entities import (
    Producto,
    Proveedor,
    SolicitudIngreso,
)


def producto(**kwargs) -> Producto:
    base = dict(
        id=1,
        codigo="7750000000014",
        nombre="Galleta Soda",
        categoria_id=1,
        precio=Decimal("3.50"),
        precio_compra_actual=Decimal("2.60"),
        stock=10,
        stock_minimo=4,
    )
    base.update(kwargs)
    return Producto(**base)  # type: ignore[arg-type]


def proveedor(**kwargs) -> Proveedor:
    base = dict(
        id=1,
        razon_social="Distribuidora Andina",
        creado_por=1,
        creado_por_nombre="Admin",
    )
    base.update(kwargs)
    return Proveedor(**base)  # type: ignore[arg-type]


class ProductoRepoFake:
    def __init__(self, productos: list[Producto] | None = None):
        self.productos = list(productos or [])
        self.alertas_marcadas: list[int] = []
        #: Todas las filas de historial generadas, en orden. Sirve para afirmar
        #: qué precios se tocaron de verdad (y cuáles no).
        self.historial: list = []
        self.eliminados: list[int] = []
        self._correlativo = 0

    def _buscar(self, producto_id):
        return next((p for p in self.productos if p.id == producto_id), None)

    async def buscar_por_id(self, producto_id: int) -> Producto | None:
        return self._buscar(producto_id)

    async def find_by_id_for_update(self, producto_id: int) -> Producto | None:
        return self._buscar(producto_id)

    async def buscar_por_codigo(self, codigo: str) -> Producto | None:
        return next(
            (p for p in self.productos if p.codigo == codigo and not p.eliminado), None
        )

    async def existe_codigo(self, codigo: str) -> bool:
        # Mira TAMBIÉN los borrados: el UNIQUE de la BD es por código vivo,
        # pero el caso de uso quiere avisar antes con un mensaje claro.
        return any(p.codigo == codigo for p in self.productos)

    async def siguiente_correlativo_interno(self, prefijo: str) -> int:
        self._correlativo += 1
        return self._correlativo

    async def crear(self, p: Producto) -> Producto:
        p.id = (max((x.id or 0) for x in self.productos) + 1) if self.productos else 1
        self.productos.append(p)
        return p

    async def incrementar_stock_atomic(self, producto_id: int, delta: int):
        """Devuelve (ok, stock_resultante).

        Reproduce el `UPDATE ... WHERE stock + delta >= 0` real: si no alcanza,
        no toca nada y avisa que falló.
        """
        p = self._buscar(producto_id)
        if p is None:
            return False, 0
        if p.stock + delta < 0:
            return False, p.stock
        p.stock += delta
        # HU-B13: al superar de nuevo el mínimo, la alerta se rearma sola.
        if p.stock > p.stock_minimo:
            p.alerta_stock_notificada = False
        return True, p.stock

    async def marcar_alerta_si_nueva(self, producto_id: int) -> bool:
        p = self._buscar(producto_id)
        if p is None or p.alerta_stock_notificada:
            return False
        p.alerta_stock_notificada = True
        self.alertas_marcadas.append(producto_id)
        return True

    async def actualizar_precio(
        self,
        producto_id: int,
        precio_venta: Decimal | None,
        precio_compra_actual: Decimal | None,
        usuario_id: int,
        usuario_nombre: str,
    ) -> tuple[Producto, list]:
        """Devuelve (producto, filas_historial), igual que el repo real.

        Sólo genera fila de historial si el precio CAMBIÓ: reescribir el mismo
        importe no es un cambio de precio y no debe ensuciar el histórico.
        """
        from app.modules.modulo_b_inventario.domain.entities import HistorialPrecio
        from app.modules.modulo_b_inventario.domain.value_objects import TipoPrecio

        p = self._buscar(producto_id)
        filas: list = []
        if precio_venta is not None and p.precio != Decimal(str(precio_venta)):
            filas.append(
                HistorialPrecio(
                    id=None,
                    producto_id=producto_id,
                    precio_anterior=p.precio,
                    precio_nuevo=Decimal(str(precio_venta)),
                    tipo_precio=TipoPrecio(TipoPrecio.VENTA),
                    modificado_por=usuario_id,
                    modificado_por_nombre=usuario_nombre,
                )
            )
            p.precio = Decimal(str(precio_venta))
        if precio_compra_actual is not None and p.precio_compra_actual != Decimal(
            str(precio_compra_actual)
        ):
            filas.append(
                HistorialPrecio(
                    id=None,
                    producto_id=producto_id,
                    precio_anterior=p.precio_compra_actual,
                    precio_nuevo=Decimal(str(precio_compra_actual)),
                    tipo_precio=TipoPrecio(TipoPrecio.COMPRA),
                    modificado_por=usuario_id,
                    modificado_por_nombre=usuario_nombre,
                )
            )
            p.precio_compra_actual = Decimal(str(precio_compra_actual))
        self.historial.extend(filas)
        return p, filas

    async def actualizar_general(self, producto_id: int, cambios: dict, *args, **kwargs) -> Producto:
        p = self._buscar(producto_id)
        for k, v in cambios.items():
            setattr(p, k, v)
        return p

    async def find_bajo_minimo(self, **kwargs) -> list[Producto]:
        solo_no_notificadas = kwargs.get("solo_no_notificadas", False)
        categoria_id = kwargs.get("categoria_id")
        res = [p for p in self.productos if p.requiere_reposicion()]
        if categoria_id is not None:
            res = [p for p in res if p.categoria_id == categoria_id]
        if solo_no_notificadas:
            res = [p for p in res if not p.alerta_stock_notificada]
        return res

    async def listar_paginado(self, **kwargs):
        vivos = [p for p in self.productos if not p.eliminado]
        return vivos, len(vivos)

    async def marcar_alertas_notificadas(self, producto_ids: list[int]) -> int:
        n = 0
        for pid in producto_ids:
            p = self._buscar(pid)
            if p is not None and not p.alerta_stock_notificada:
                p.alerta_stock_notificada = True
                n += 1
        return n

    async def eliminar(self, producto_id: int, usuario_id: int) -> Producto:
        from datetime import datetime, timezone

        p = self._buscar(producto_id)
        p.deleted_at = datetime.now(timezone.utc)
        p.deleted_by = usuario_id
        p.activo = False
        self.eliminados.append(producto_id)
        return p


class MovimientoRepoFake:
    def __init__(self):
        self.movimientos: list = []

    async def append(self, movimiento):
        movimiento.id = len(self.movimientos) + 1
        self.movimientos.append(movimiento)
        return movimiento

    def tipos(self) -> list[str]:
        return [str(m.tipo) for m in self.movimientos]


class HistorialPrecioRepoFake:
    def __init__(self):
        self.filas: list = []

    async def append(self, fila):
        fila.id = len(self.filas) + 1
        self.filas.append(fila)
        return fila


class SolicitudRepoFake:
    def __init__(self, solicitudes: list[SolicitudIngreso] | None = None):
        self.solicitudes = list(solicitudes or [])
        self.actualizadas: list = []

    async def find_by_id(self, solicitud_id: int):
        return next((s for s in self.solicitudes if s.id == solicitud_id), None)

    async def find_by_id_for_update(self, solicitud_id: int):
        return await self.find_by_id(solicitud_id)

    async def crear(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        solicitud.id = len(self.solicitudes) + 1
        self.solicitudes.append(solicitud)
        return solicitud

    async def actualizar(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        self.actualizadas.append(solicitud)
        return solicitud


class DetalleRepoFake:
    def __init__(self, por_solicitud: dict[int, list] | None = None):
        self.por_solicitud = por_solicitud or {}
        self.creados: list = []

    async def listar_por_solicitud(self, solicitud_id: int) -> list:
        return list(self.por_solicitud.get(solicitud_id, []))

    async def crear_bulk(self, detalles: list) -> list:
        self.creados.extend(detalles)
        for d in detalles:
            self.por_solicitud.setdefault(d.solicitud_id, []).append(d)
        return detalles

    async def eliminar_por_solicitud(self, solicitud_id: int) -> None:
        self.por_solicitud[solicitud_id] = []

    async def asignar_producto(self, detalle_id: int, producto_id: int) -> None:
        for lineas in self.por_solicitud.values():
            for d in lineas:
                if d.id == detalle_id:
                    d.producto_id = producto_id


class ProveedorRepoFake:
    def __init__(self, proveedores: list[Proveedor] | None = None):
        self.proveedores = list(proveedores or [])
        self.deudas_actualizadas: list = []

    async def find_by_id(self, proveedor_id: int):
        return next((p for p in self.proveedores if p.id == proveedor_id), None)

    async def find_by_id_for_update(self, proveedor_id: int):
        return await self.find_by_id(proveedor_id)

    async def buscar_por_id(self, proveedor_id: int):
        return await self.find_by_id(proveedor_id)

    async def find_by_ruc(self, ruc: str):
        return next(
            (p for p in self.proveedores if p.ruc == ruc and not p.eliminado), None
        )

    async def crear(self, prov: Proveedor) -> Proveedor:
        prov.id = len(self.proveedores) + 1
        self.proveedores.append(prov)
        return prov

    async def actualizar(self, prov: Proveedor) -> Proveedor:
        return prov

    async def incrementar_deuda_atomic(self, proveedor_id: int, delta) -> bool:
        """Reproduce el UPDATE condicional: la deuda nunca queda negativa."""
        p = await self.find_by_id(proveedor_id)
        if p is None or p.deuda_actual + delta < 0:
            return False
        p.deuda_actual += delta
        self.deudas_actualizadas.append((proveedor_id, delta))
        return True


class AuditoriaFake:
    def __init__(self):
        self.eventos: list[dict] = []

    async def ejecutar(self, **kwargs):
        self.eventos.append(kwargs)

    def acciones(self) -> list[str]:
        return [e.get("accion") for e in self.eventos]


class NotificadorFake:
    """Misma firma que `Notificador.avisar`: tipo/título/mensaje posicionales."""

    def __init__(self):
        self.avisos: list[dict] = []

    async def avisar(self, tipo, titulo, mensaje, **kwargs):
        self.avisos.append(
            {"tipo": tipo, "titulo": titulo, "mensaje": mensaje, **kwargs}
        )

    def tipos(self) -> list[str]:
        # `tipo` es un enum: interesa su valor ("STOCK_BAJO"), no su repr.
        return [getattr(a["tipo"], "value", str(a["tipo"])) for a in self.avisos]


class CategoriaRepoFake:
    def __init__(self, categorias: list | None = None):
        self.categorias = list(categorias or [])
        self.creadas: list = []

    async def find_by_id(self, categoria_id: int):
        return next((c for c in self.categorias if c.id == categoria_id), None)

    async def buscar_por_id(self, categoria_id: int):
        return await self.find_by_id(categoria_id)

    async def existe_nombre(self, nombre: str) -> bool:
        return any(c.nombre == nombre for c in self.categorias)

    async def crear(self, categoria):
        categoria.id = len(self.categorias) + 1
        self.categorias.append(categoria)
        self.creadas.append(categoria)
        return categoria


class PagoProveedorRepoFake:
    def __init__(self):
        self.pagos: list = []

    async def crear(self, pago):
        pago.id = len(self.pagos) + 1
        self.pagos.append(pago)
        return pago

    def tipos(self) -> list[str]:
        return [str(p.tipo) for p in self.pagos]
