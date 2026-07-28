"""Anulaciones y devoluciones: cuando la plata vuelve al cliente.

La venta original NUNCA se borra: se marca y queda el rastro (RF-22). Lo que
importa es que tres cosas queden consistentes:
  - el stock vuelve al inventario;
  - del cajón sale sólo lo que había entrado EN EFECTIVO (una venta por Yape
    se revierte, pero de la caja no sale nada);
  - no se puede devolver más de lo que se compró, ni devolver dos veces.
"""

from decimal import Decimal

import pytest

from app.modules.modulo_c_ventas.application.anular_venta_usecase import (
    AnularVentaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import (
    DetalleVenta,
    PagoVenta,
    Venta,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    CajaRepoFake,
    StockFake,
    VentaRepoFake,
    turno,
    vendible,
)

CTX = dict(usuario_id=2, nombre_usuario="Ana Torres")


def detalle(id=1, producto_id=1, precio="10.00", cantidad=2, devuelta=0) -> DetalleVenta:
    return DetalleVenta(
        id=id,
        producto_id=producto_id,
        nombre="Galleta Soda",
        precio_unitario=Decimal(precio),
        cantidad=cantidad,
        cantidad_devuelta=devuelta,
    )


def venta_efectivo(**kwargs) -> Venta:
    base = dict(
        id=1,
        turno_id=1,
        usuario_id=2,
        vendedor="Ana Torres",
        total=Decimal("20.00"),
        metodo_pago="EFECTIVO",
        detalles=[detalle()],
        pagos=[
            PagoVenta(
                id=1, codigo_metodo="EFECTIVO", monto=Decimal("20.00"),
                es_efectivo=True,
            )
        ],
    )
    base.update(kwargs)
    return Venta(**base)  # type: ignore[arg-type]


class Escenario:
    def __init__(self, ventas=None, abierto=True, productos=None):
        self.ventas = VentaRepoFake(
            ventas if ventas is not None else [venta_efectivo()]
        )
        self.caja = CajaRepoFake(turno() if abierto else None)
        self.stock = StockFake(productos if productos is not None else [vendible(stock=5)])
        self.auditoria = AuditoriaFake()
        self.caso = AnularVentaUseCase(
            self.ventas, self.caja, self.stock, self.auditoria
        )


class TestAnularVenta:
    async def test_marca_la_venta_como_anulada(self):
        e = Escenario()
        await e.caso.anular(venta_id=1, motivo="El cliente se arrepintió", **CTX)
        assert e.ventas.ventas[0].anulada is True

    async def test_la_venta_no_se_borra(self):
        """Queda como rastro: los reportes tienen que poder excluirla, no
        perderla."""
        e = Escenario()
        await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)
        assert len(e.ventas.ventas) == 1

    async def test_repone_el_stock(self):
        p = vendible(id=1, stock=5)
        e = Escenario(productos=[p])
        await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)
        assert p.stock == 7, "vuelven las 2 unidades vendidas"

    async def test_devuelve_el_efectivo_de_la_venta(self):
        e = Escenario()
        a = await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)
        assert a.efectivo_devuelto == Decimal("20.00")

    async def test_una_venta_por_yape_no_saca_plata_del_cajon(self):
        """Se revierte el monto, pero del cajón no salió nada: si se descontara,
        la caja cerraría con faltante."""
        v = venta_efectivo(
            metodo_pago="YAPE",
            pagos=[
                PagoVenta(
                    id=1, codigo_metodo="YAPE", monto=Decimal("20.00"),
                    es_efectivo=False,
                )
            ],
        )
        e = Escenario([v])
        a = await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)
        assert a.monto == Decimal("20.00")
        assert a.efectivo_devuelto == Decimal("0")

    async def test_una_venta_mixta_solo_devuelve_la_parte_en_efectivo(self):
        v = venta_efectivo(
            total=Decimal("20.00"),
            metodo_pago="MIXTO",
            pagos=[
                PagoVenta(id=1, codigo_metodo="EFECTIVO", monto=Decimal("5.00"),
                          es_efectivo=True),
                PagoVenta(id=2, codigo_metodo="YAPE", monto=Decimal("15.00"),
                          es_efectivo=False),
            ],
        )
        e = Escenario([v])
        a = await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)
        assert a.efectivo_devuelto == Decimal("5.00")

    async def test_el_reverso_se_carga_al_turno_ACTUAL(self):
        """Si se anula al día siguiente, la plata sale de la caja de HOY."""
        v = venta_efectivo(turno_id=1)
        e = Escenario([v])
        e.caja._abierto = turno(id=9)
        a = await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)
        assert a.turno_id == 9

    @pytest.mark.parametrize("motivo", ["", "   "])
    async def test_el_motivo_es_obligatorio(self, motivo):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.caso.anular(venta_id=1, motivo=motivo, **CTX)

    async def test_venta_inexistente(self):
        e = Escenario([])
        with pytest.raises(NoEncontradoError):
            await e.caso.anular(venta_id=404, motivo="lo que sea", **CTX)

    async def test_no_se_puede_anular_dos_veces(self):
        e = Escenario()
        await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)
        with pytest.raises(ConflictoError):
            await e.caso.anular(venta_id=1, motivo="otra vez", **CTX)

    async def test_sin_turno_abierto_no_se_puede_revertir(self):
        """El reverso mueve plata: necesita una caja donde registrarse."""
        e = Escenario(abierto=False)
        with pytest.raises(ConflictoError):
            await e.caso.anular(venta_id=1, motivo="error de carga", **CTX)

    async def test_el_motivo_queda_en_la_venta(self):
        e = Escenario()
        await e.caso.anular(venta_id=1, motivo="El cliente se arrepintió", **CTX)
        assert e.ventas.ventas[0].motivo_anulacion == "El cliente se arrepintió"


class TestDevolucionParcial:
    async def test_repone_solo_lo_devuelto(self):
        p = vendible(id=1, stock=5)
        e = Escenario([venta_efectivo(detalles=[detalle(cantidad=3)])], productos=[p])
        await e.caso.devolver(
            venta_id=1, items=[(1, 1)], motivo="una vino fallada", **CTX
        )
        assert p.stock == 6

    async def test_la_venta_NO_queda_anulada(self):
        """Una devolución parcial no invalida la venta entera."""
        e = Escenario([venta_efectivo(detalles=[detalle(cantidad=3)])])
        await e.caso.devolver(
            venta_id=1, items=[(1, 1)], motivo="una vino fallada", **CTX
        )
        assert e.ventas.ventas[0].anulada is False

    async def test_marca_la_cantidad_devuelta_en_la_linea(self):
        d = detalle(cantidad=3)
        e = Escenario([venta_efectivo(detalles=[d])])
        await e.caso.devolver(
            venta_id=1, items=[(1, 2)], motivo="vinieron falladas", **CTX
        )
        assert d.cantidad_devuelta == 2

    async def test_el_monto_es_proporcional_a_lo_devuelto(self):
        e = Escenario(
            [venta_efectivo(detalles=[detalle(precio="10.00", cantidad=3)])]
        )
        a = await e.caso.devolver(
            venta_id=1, items=[(1, 2)], motivo="vinieron falladas", **CTX
        )
        assert a.monto == Decimal("20.00")

    async def test_no_se_puede_devolver_mas_de_lo_comprado(self):
        e = Escenario([venta_efectivo(detalles=[detalle(cantidad=2)])])
        with pytest.raises(ValidacionError):
            await e.caso.devolver(
                venta_id=1, items=[(1, 3)], motivo="lo que sea", **CTX
            )

    async def test_no_se_puede_devolver_dos_veces_lo_mismo(self):
        """La segunda devolución ya no tiene unidades disponibles."""
        e = Escenario([venta_efectivo(detalles=[detalle(cantidad=2)])])
        await e.caso.devolver(venta_id=1, items=[(1, 2)], motivo="falladas", **CTX)
        with pytest.raises(ValidacionError):
            await e.caso.devolver(venta_id=1, items=[(1, 1)], motivo="otra vez", **CTX)

    @pytest.mark.parametrize("cantidad", [0, -1])
    async def test_cantidad_invalida(self, cantidad):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.caso.devolver(
                venta_id=1, items=[(1, cantidad)], motivo="lo que sea", **CTX
            )

    async def test_sin_items(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.caso.devolver(venta_id=1, items=[], motivo="lo que sea", **CTX)

    async def test_una_linea_de_otra_venta(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.caso.devolver(
                venta_id=1, items=[(999, 1)], motivo="lo que sea", **CTX
            )

    async def test_el_efectivo_devuelto_no_supera_lo_que_entro(self):
        """Tras varias devoluciones parciales no puede salir del cajón más
        plata de la que la venta aportó."""
        e = Escenario(
            [venta_efectivo(detalles=[detalle(precio="10.00", cantidad=2)])]
        )
        a1 = await e.caso.devolver(
            venta_id=1, items=[(1, 1)], motivo="una fallada", **CTX
        )
        a2 = await e.caso.devolver(
            venta_id=1, items=[(1, 1)], motivo="la otra también", **CTX
        )
        assert a1.efectivo_devuelto + a2.efectivo_devuelto <= Decimal("20.00")
