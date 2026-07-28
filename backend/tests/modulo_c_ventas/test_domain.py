"""Dominio del Módulo C: ventas y caja.

La regla que atraviesa todo es la distinción entre **dinero físico** y **dinero
digital**. En el arqueo sólo se cuenta lo que está en el cajón: si una venta se
pagó con Yape, ese dinero existe pero no está ahí. Confundirlos hace que la caja
"no cuadre" todos los días.

El otro eje son los **snapshots**: nombre del producto, precio y nombre del
vendedor se copian al momento de la venta. Si mañana cambia el precio, el ticket
viejo y los reportes históricos no se alteran.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.modules.modulo_c_ventas.domain.entities import (
    Anulacion,
    ArqueoCaja,
    DetalleVenta,
    PagoVenta,
    TurnoCaja,
    Venta,
)
from app.modules.modulo_c_ventas.domain.value_objects import monto_dinero
from app.shared.kernel.exceptions import ValidacionError

AHORA = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def pago(monto="10.00", efectivo=True, recibido=None, codigo="EFECTIVO") -> PagoVenta:
    return PagoVenta(
        id=None,
        codigo_metodo=codigo,
        monto=Decimal(monto),
        es_efectivo=efectivo,
        monto_recibido=Decimal(recibido) if recibido is not None else None,
    )


def venta(**kwargs) -> Venta:
    base = dict(
        id=1,
        turno_id=1,
        usuario_id=2,
        vendedor="Ana Torres",
        total=Decimal("10.00"),
        metodo_pago="EFECTIVO",
    )
    base.update(kwargs)
    return Venta(**base)  # type: ignore[arg-type]


class TestTurnoCaja:
    def test_nace_abierto(self):
        t = TurnoCaja(
            id=1, usuario_id=1, abierto_por="Ana", monto_inicial=Decimal("100")
        )
        assert t.esta_abierto() is True

    def test_cerrado_ya_no_esta_abierto(self):
        t = TurnoCaja(
            id=1, usuario_id=1, abierto_por="Ana",
            monto_inicial=Decimal("100"), estado="CERRADO",
        )
        assert t.esta_abierto() is False

    def test_el_nombre_de_quien_abrio_es_snapshot(self):
        """Si renombran al usuario, el turno viejo sigue diciendo quién lo abrió."""
        t = TurnoCaja(
            id=1, usuario_id=1, abierto_por="Ana Torres", monto_inicial=Decimal("0")
        )
        assert t.abierto_por == "Ana Torres"


class TestArqueoCaja:
    def _arqueo(self, esperado="100", contado="100") -> ArqueoCaja:
        e, c = Decimal(esperado), Decimal(contado)
        return ArqueoCaja(
            id=None, turno_id=1, usuario_id=1, cerrado_por="Ana",
            efectivo_esperado=e, efectivo_contado=c, diferencia=c - e,
        )

    def test_cuadra_cuando_no_hay_diferencia(self):
        assert self._arqueo("100", "100").cuadrado is True

    def test_faltante_no_cuadra(self):
        a = self._arqueo("100", "95")
        assert a.cuadrado is False
        assert a.diferencia == Decimal("-5"), "el faltante es negativo"

    def test_sobrante_tampoco_cuadra(self):
        """Que sobre plata también es un descuadre: hay que explicarlo."""
        a = self._arqueo("100", "105")
        assert a.cuadrado is False
        assert a.diferencia == Decimal("5")

    def test_una_diferencia_de_un_centavo_ya_es_descuadre(self):
        assert self._arqueo("100.00", "100.01").cuadrado is False


class TestPagoVentaYVuelto:
    def test_sin_monto_recibido_no_hay_vuelto(self):
        """Los pagos digitales son por el importe exacto."""
        assert pago(monto="10.00", efectivo=False).vuelto == Decimal("0")

    def test_paga_justo_no_hay_vuelto(self):
        assert pago(monto="10.00", recibido="10.00").vuelto == Decimal("0")

    def test_paga_de_mas_hay_vuelto(self):
        assert pago(monto="10.00", recibido="20.00").vuelto == Decimal("10.00")

    def test_el_vuelto_nunca_es_negativo(self):
        """Si recibió menos que el total, falta plata: no es un vuelto negativo."""
        assert pago(monto="10.00", recibido="5.00").vuelto == Decimal("0")


class TestDetalleVenta:
    def test_el_subtotal_es_precio_por_cantidad(self):
        d = DetalleVenta(
            id=None, producto_id=1, nombre="Galleta",
            precio_unitario=Decimal("3.50"), cantidad=3,
        )
        assert d.subtotal == Decimal("10.50")

    def test_el_nombre_y_el_precio_son_snapshot(self):
        """El ticket viejo no puede cambiar si mañana sube el precio (RF-18)."""
        d = DetalleVenta(
            id=None, producto_id=1, nombre="Galleta Soda",
            precio_unitario=Decimal("3.50"), cantidad=1,
        )
        assert d.nombre == "Galleta Soda"
        assert d.precio_unitario == Decimal("3.50")

    def test_nace_sin_devoluciones(self):
        d = DetalleVenta(
            id=None, producto_id=1, nombre="X",
            precio_unitario=Decimal("1"), cantidad=5,
        )
        assert d.cantidad_devuelta == 0


class TestVentaEfectivoVsDigital:
    def test_venta_en_efectivo_entra_entera_al_cajon(self):
        v = venta(pagos=[pago(monto="10.00", efectivo=True)])
        assert v.total_efectivo == Decimal("10.00")

    def test_venta_por_yape_NO_entra_al_cajon(self):
        """Existe la plata, pero no está físicamente en la caja: si se contara,
        el arqueo daría faltante todos los días."""
        v = venta(pagos=[pago(monto="10.00", efectivo=False, codigo="YAPE")])
        assert v.total_efectivo == Decimal("0")

    def test_venta_mixta_solo_suma_la_parte_en_efectivo(self):
        v = venta(
            total=Decimal("30.00"),
            metodo_pago="MIXTO",
            pagos=[
                pago(monto="10.00", efectivo=True),
                pago(monto="20.00", efectivo=False, codigo="YAPE"),
            ],
        )
        assert v.total_efectivo == Decimal("10.00")

    def test_el_vuelto_de_la_venta_suma_el_de_sus_pagos(self):
        v = venta(pagos=[pago(monto="10.00", recibido="50.00")])
        assert v.vuelto == Decimal("40.00")

    def test_una_venta_sin_pagos_no_aporta_efectivo(self):
        assert venta(pagos=[]).total_efectivo == Decimal("0")


class TestVentaAnulada:
    def test_una_venta_normal_no_esta_anulada(self):
        assert venta().anulada is False

    def test_una_anulada_se_reconoce(self):
        v = venta(estado="ANULADA")
        assert v.anulada is True

    def test_la_venta_anulada_conserva_su_motivo(self):
        """Nunca se borra: queda como rastro (RF-22)."""
        v = venta(estado="ANULADA", motivo_anulacion="El cliente se arrepintió")
        assert v.motivo_anulacion == "El cliente se arrepintió"


class TestAnulacion:
    def test_guarda_en_que_turno_se_hizo_el_reverso(self):
        """Puede ser distinto al turno de la venta: la plata sale de ESA caja."""
        a = Anulacion(
            id=None, venta_id=1, turno_id=9, tipo="ANULACION", usuario_id=2,
            realizado_por="Ana", motivo="error de carga",
            monto=Decimal("10"), efectivo_devuelto=Decimal("10"), items=None,
        )
        assert a.turno_id == 9

    def test_el_efectivo_devuelto_puede_ser_menor_al_monto(self):
        """Si la venta fue por Yape, se revierte el monto pero del cajón no sale
        nada."""
        a = Anulacion(
            id=None, venta_id=1, turno_id=1, tipo="ANULACION", usuario_id=2,
            realizado_por="Ana", motivo="pagó por Yape",
            monto=Decimal("30"), efectivo_devuelto=Decimal("0"), items=None,
        )
        assert a.monto == Decimal("30")
        assert a.efectivo_devuelto == Decimal("0")


class TestMontoDinero:
    @pytest.mark.parametrize("valor", ["10", "10.50", 10, 10.5, Decimal("0")])
    def test_acepta_montos_validos(self, valor):
        assert monto_dinero(valor) >= Decimal("0")

    def test_normaliza_a_decimal(self):
        """Con float, 0.1 + 0.2 no da 0.3 y la caja se desfasa."""
        assert isinstance(monto_dinero(10.5), Decimal)

    def test_rechaza_negativos_por_defecto(self):
        with pytest.raises(ValidacionError):
            monto_dinero("-1")

    def test_permite_negativos_si_se_pide(self):
        assert monto_dinero("-5", minimo=None) == Decimal("-5")

    def test_rechaza_lo_que_no_es_numero(self):
        with pytest.raises(ValidacionError):
            monto_dinero("diez")
