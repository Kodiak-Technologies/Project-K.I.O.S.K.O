"""`AprobarIngresoUseCase`: el momento en que la mercadería entra al inventario.

Es el caso de uso más delicado del módulo porque toca tres cosas a la vez y
todas tienen que quedar consistentes:
  1. sube el stock de cada producto y deja su asiento;
  2. el precio de compra de la boleta pasa a ser el precio vigente del producto;
  3. opcionalmente carga la compra a la deuda del proveedor.

Y no puede aprobarse dos veces: eso duplicaría el stock ingresado.
"""

from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.aprobar_ingreso_usecase import (
    AprobarIngresoUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    DetalleSolicitud,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    DetalleRepoFake,
    MovimientoRepoFake,
    ProductoRepoFake,
    SolicitudRepoFake,
    producto,
)

CTX = dict(usuario_id=9, usuario_nombre="Admin", ip="", user_agent="")


def solicitud(**kwargs) -> SolicitudIngreso:
    base = dict(
        id=1,
        estado=EstadoSolicitud(EstadoSolicitud.PENDIENTE),
        proveedor_id=7,
        foto_boleta_url="https://drive/b.png",
        solicitado_por=2,
        solicitado_por_nombre="Cajero",
    )
    base.update(kwargs)
    return SolicitudIngreso(**base)  # type: ignore[arg-type]


def linea(producto_id=1, cantidad=10, precio="2.00") -> DetalleSolicitud:
    return DetalleSolicitud(
        id=None,
        solicitud_id=1,
        producto_id=producto_id,
        cantidad=cantidad,
        precio_compra_unitario=Decimal(precio),
    )


class CompraCreditoFake:
    def __init__(self):
        self.llamadas: list[dict] = []

    async def ejecutar(self, **kwargs):
        self.llamadas.append(kwargs)


class Escenario:
    def __init__(self, sol=None, lineas=None, productos=None):
        self.solicitud = sol if sol is not None else solicitud()
        self.solicitudes = SolicitudRepoFake([self.solicitud] if self.solicitud else [])
        self.detalles = DetalleRepoFake({1: lineas if lineas is not None else [linea()]})
        self.productos = ProductoRepoFake(
            productos if productos is not None else [producto(id=1, stock=5)]
        )
        self.movimientos = MovimientoRepoFake()
        self.auditoria = AuditoriaFake()
        self.credito = CompraCreditoFake()
        self.caso = AprobarIngresoUseCase(
            self.solicitudes,
            self.detalles,
            self.productos,
            self.movimientos,
            self.auditoria,
            self.credito,
        )

    async def aprobar(self, solicitud_id=1, registrar_credito=False):
        return await self.caso.ejecutar(
            solicitud_id=solicitud_id, registrar_credito=registrar_credito, **CTX
        )


class TestAprobacionExitosa:
    async def test_sube_el_stock_de_cada_linea(self):
        p = producto(id=1, stock=5)
        e = Escenario(lineas=[linea(producto_id=1, cantidad=10)], productos=[p])
        await e.aprobar()
        assert p.stock == 15

    async def test_deja_un_asiento_de_ingreso_por_linea(self):
        e = Escenario(
            lineas=[linea(producto_id=1, cantidad=4), linea(producto_id=2, cantidad=6)],
            productos=[producto(id=1, stock=0), producto(id=2, stock=0)],
        )
        await e.aprobar()
        assert e.movimientos.tipos() == ["ingreso", "ingreso"]

    async def test_el_asiento_queda_vinculado_a_la_solicitud(self):
        e = Escenario()
        await e.aprobar()
        assert e.movimientos.movimientos[0].solicitud_ingreso_id == 1

    async def test_marca_la_solicitud_como_aprobada(self):
        e = Escenario()
        r = await e.aprobar()
        assert r.solicitud.estado == EstadoSolicitud(EstadoSolicitud.APROBADA)
        assert r.solicitud.revisado_por == 9

    async def test_informa_cuantos_productos_y_unidades_entraron(self):
        e = Escenario(
            lineas=[linea(producto_id=1, cantidad=4), linea(producto_id=2, cantidad=6)],
            productos=[producto(id=1, stock=0), producto(id=2, stock=0)],
        )
        r = await e.aprobar()
        assert r.productos_actualizados == 2
        assert r.unidades_agregadas == 10

    async def test_calcula_el_monto_total_de_la_compra(self):
        e = Escenario(
            lineas=[
                linea(producto_id=1, cantidad=10, precio="2.50"),
                linea(producto_id=2, cantidad=4, precio="3.00"),
            ],
            productos=[producto(id=1, stock=0), producto(id=2, stock=0)],
        )
        r = await e.aprobar()
        assert r.monto_total == Decimal("37.00")  # 25 + 12

    async def test_el_precio_de_compra_de_la_boleta_llega_al_producto(self):
        """Antes moría en el detalle y el catálogo quedaba con el precio viejo."""
        p = producto(id=1, stock=0, precio_compra_actual=Decimal("1.00"))
        e = Escenario(lineas=[linea(producto_id=1, precio="2.75")], productos=[p])
        await e.aprobar()
        assert p.precio_compra_actual == Decimal("2.75")

    async def test_queda_registrado_en_bitacora(self):
        e = Escenario()
        await e.aprobar()
        assert e.auditoria.eventos


class TestAprobacionRechazada:
    async def test_solicitud_inexistente(self):
        e = Escenario(sol=None)
        with pytest.raises(NoEncontradoError):
            await e.aprobar(solicitud_id=404)

    async def test_no_se_puede_aprobar_dos_veces(self):
        """Duplicaría el stock ingresado."""
        e = Escenario()
        await e.aprobar()
        with pytest.raises(ConflictoError):
            await e.aprobar()

    async def test_una_rechazada_no_se_puede_aprobar(self):
        s = solicitud()
        s.rechazar(usuario_id=9, nombre="Admin", motivo="boleta ilegible")
        e = Escenario(sol=s)
        with pytest.raises(ConflictoError):
            await e.aprobar()

    async def test_si_una_linea_falla_se_corta(self):
        """El repo devuelve ok=False cuando el producto no existe: la
        aprobación no puede seguir a medias."""
        e = Escenario(
            lineas=[linea(producto_id=1), linea(producto_id=404)],
            productos=[producto(id=1, stock=0)],
        )
        with pytest.raises(ConflictoError):
            await e.aprobar()

    async def test_la_solicitud_sigue_pendiente_si_falla_una_linea(self):
        s = solicitud()
        e = Escenario(
            sol=s,
            lineas=[linea(producto_id=404)],
            productos=[producto(id=1, stock=0)],
        )
        with pytest.raises(ConflictoError):
            await e.aprobar()
        assert s.estado == EstadoSolicitud(EstadoSolicitud.PENDIENTE)


class TestCompraACredito:
    async def test_no_registra_credito_si_no_se_pide(self):
        e = Escenario()
        r = await e.aprobar(registrar_credito=False)
        assert r.credito_registrado is False
        assert e.credito.llamadas == []

    async def test_registra_la_deuda_por_el_monto_total(self):
        e = Escenario(lineas=[linea(cantidad=10, precio="2.00")])
        r = await e.aprobar(registrar_credito=True)
        assert r.credito_registrado is True
        assert e.credito.llamadas[0]["monto"] == Decimal("20.00")

    async def test_la_deuda_queda_vinculada_al_proveedor_de_la_solicitud(self):
        e = Escenario(sol=solicitud(proveedor_id=7))
        await e.aprobar(registrar_credito=True)
        assert e.credito.llamadas[0]["proveedor_id"] == 7

    async def test_sin_proveedor_no_se_puede_cargar_a_credito(self):
        """A quién se le debería la plata sería indefinido."""
        e = Escenario(sol=solicitud(proveedor_id=None))
        with pytest.raises(ValidacionError):
            await e.aprobar(registrar_credito=True)

    async def test_una_solicitud_sin_lineas_no_genera_deuda(self):
        e = Escenario(lineas=[])
        r = await e.aprobar(registrar_credito=True)
        assert r.credito_registrado is False
        assert e.credito.llamadas == []
