"""Dobles en memoria de los puertos del Módulo C."""

from __future__ import annotations

from decimal import Decimal

from app.modules.modulo_c_ventas.domain.entities import (
    MetodoPago,
    ProductoVendible,
    TurnoCaja,
    Venta,
)

METODOS_POR_DEFECTO = [
    MetodoPago(id=1, codigo="EFECTIVO", nombre="Efectivo", es_efectivo=True, activo=True),
    MetodoPago(id=2, codigo="YAPE", nombre="Yape", es_efectivo=False, activo=True),
    MetodoPago(id=3, codigo="TARJETA", nombre="Tarjeta", es_efectivo=False, activo=True),
]


def turno(**kwargs) -> TurnoCaja:
    base = dict(
        id=1, usuario_id=2, abierto_por="Ana Torres", monto_inicial=Decimal("100")
    )
    base.update(kwargs)
    return TurnoCaja(**base)  # type: ignore[arg-type]


def vendible(**kwargs) -> ProductoVendible:
    base = dict(
        id=1,
        codigo="7750000000014",
        nombre="Galleta Soda",
        precio=Decimal("3.50"),
        stock=10,
        activo=True,
        stock_minimo=2,
    )
    base.update(kwargs)
    return ProductoVendible(**base)  # type: ignore[arg-type]


class CajaRepoFake:
    def __init__(self, abierto: TurnoCaja | None = None, turnos=None):
        self._abierto = abierto
        self.turnos = list(turnos or ([abierto] if abierto else []))
        self.arqueos: list = []
        self.cerrados: list = []
        # Mismas claves que devuelve el repo real (ver `calcular_resumen`).
        self.totales = {
            "ventas_efectivo": Decimal("0"),
            "devoluciones_efectivo": Decimal("0"),
            "totales_por_metodo": {},
            "total_vendido": Decimal("0"),
            "numero_ventas": 0,
        }

    async def turno_abierto(self) -> TurnoCaja | None:
        return self._abierto

    async def buscar_por_id(self, turno_id: int) -> TurnoCaja | None:
        return next((t for t in self.turnos if t.id == turno_id), None)

    async def abrir(self, t: TurnoCaja) -> TurnoCaja:
        t.id = len(self.turnos) + 1
        self.turnos.append(t)
        self._abierto = t
        return t

    async def actualizar(self, t: TurnoCaja) -> TurnoCaja:
        return t

    async def listar(self, limite: int = 30) -> list[TurnoCaja]:
        return self.turnos[:limite]

    async def cerrar(self, *args, **kwargs):
        self.cerrados.append((args, kwargs))
        if self._abierto is not None:
            self._abierto.estado = "CERRADO"
        cerrado = self._abierto
        self._abierto = None
        return cerrado

    async def guardar_arqueo(self, arqueo):
        arqueo.id = len(self.arqueos) + 1
        self.arqueos.append(arqueo)
        return arqueo

    async def arqueos_por_turno(self, turno_ids: list[int]) -> dict:
        return {a.turno_id: a for a in self.arqueos if a.turno_id in turno_ids}

    async def totales_de_turno(self, turno_id: int) -> dict:
        return dict(self.totales)


class StockFake:
    """Simula el UPDATE atómico del inventario: el stock nunca queda negativo."""

    def __init__(self, productos: list[ProductoVendible] | None = None):
        self.productos = {p.id: p for p in (productos or [vendible()])}
        self.descuentos: list[tuple[int, int]] = []
        self.reposiciones: list[tuple[int, int]] = []
        self.alertas: list[int] = []
        self._ya_avisados: set[int] = set()

    async def obtener_para_venta(self, producto_ids: list[int]) -> dict:
        return {pid: self.productos[pid] for pid in producto_ids if pid in self.productos}

    async def descontar_stock(
        self, producto_id: int, cantidad: int, usuario_id=None, usuario_nombre=""
    ) -> bool:
        p = self.productos.get(producto_id)
        if p is None or p.stock < cantidad:
            return False
        p.stock -= cantidad
        self.descuentos.append((producto_id, cantidad))
        return True

    async def marcar_alerta_stock(self, producto_id: int) -> bool:
        if producto_id in self._ya_avisados:
            return False
        self._ya_avisados.add(producto_id)
        self.alertas.append(producto_id)
        return True

    async def reponer_stock(
        self, producto_id: int, cantidad: int, usuario_id=None,
        usuario_nombre="", motivo=None,
    ) -> None:
        p = self.productos.get(producto_id)
        if p is not None:
            p.stock += cantidad
        self.reposiciones.append((producto_id, cantidad))


class MetodoPagoRepoFake:
    def __init__(self, metodos=None):
        self.metodos = list(metodos if metodos is not None else METODOS_POR_DEFECTO)

    async def listar(self, solo_activos: bool = True):
        return [m for m in self.metodos if m.activo or not solo_activos]

    async def buscar_por_codigo(self, codigo: str):
        return next((m for m in self.metodos if m.codigo == codigo), None)

    async def crear(self, metodo):
        metodo.id = len(self.metodos) + 1
        self.metodos.append(metodo)
        return metodo

    async def actualizar(self, metodo_id: int, cambios: dict):
        m = next(x for x in self.metodos if x.id == metodo_id)
        for k, v in cambios.items():
            setattr(m, k, v)
        return m


class VentaRepoFake:
    def __init__(self, ventas: list[Venta] | None = None):
        self.ventas = list(ventas or [])
        self.anulaciones: list = []

    async def crear(self, v: Venta) -> Venta:
        v.id = len(self.ventas) + 1
        self.ventas.append(v)
        return v

    async def buscar_por_id(self, venta_id: int):
        return next((v for v in self.ventas if v.id == venta_id), None)

    async def buscar_por_uuid(self, client_uuid: str):
        return next((v for v in self.ventas if v.client_uuid == client_uuid), None)

    async def actualizar(self, v: Venta) -> Venta:
        return v

    async def anulaciones_de_venta(self, venta_id: int) -> list:
        return [a for a in self.anulaciones if a.venta_id == venta_id]

    async def actualizar_estado(self, venta_id: int, estado: str, motivo: str | None = None):
        v = await self.buscar_por_id(venta_id)
        if v is not None:
            v.estado = estado
            v.motivo_anulacion = motivo
        return v

    async def registrar_devolucion_detalle(self, detalle_id: int, cantidad: int):
        for v in self.ventas:
            for d in v.detalles:
                if d.id == detalle_id:
                    d.cantidad_devuelta += cantidad
                    return d
        return None

    async def crear_anulacion(self, anulacion):
        anulacion.id = len(self.anulaciones) + 1
        self.anulaciones.append(anulacion)
        return anulacion


class AuditoriaFake:
    def __init__(self):
        self.eventos: list[dict] = []

    async def ejecutar(self, **kwargs):
        self.eventos.append(kwargs)

    def acciones(self) -> list[str]:
        return [e.get("accion") for e in self.eventos]


class NotificadorFake:
    def __init__(self):
        self.avisos: list[dict] = []

    async def avisar(self, tipo, titulo, mensaje, **kwargs):
        self.avisos.append(
            {"tipo": tipo, "titulo": titulo, "mensaje": mensaje, **kwargs}
        )

    def tipos(self) -> list[str]:
        return [getattr(a["tipo"], "value", str(a["tipo"])) for a in self.avisos]
