"""`RegistrarVentaUseCase`: el corazón del punto de venta.

Concentra varias reglas que, si fallan, se traducen en plata mal contada:
  - no se vende sin turno de caja abierto;
  - el stock se descuenta atómicamente y nunca queda negativo;
  - los pagos tienen que cubrir el total, ni más ni menos;
  - una venta pagada con más de un método se resume como MIXTO, pero el
    desglose real queda en `pagos`, que es de donde salen los reportes;
  - las ventas offline se sincronizan por `client_uuid` sin duplicarse.
"""

from decimal import Decimal

import pytest

from app.modules.modulo_c_ventas.application.registrar_venta_usecase import (
    RegistrarVentaUseCase,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ProhibidoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    CajaRepoFake,
    MetodoPagoRepoFake,
    NotificadorFake,
    StockFake,
    VentaRepoFake,
    turno,
    vendible,
)

CTX = dict(usuario_id=2, nombre_usuario="Ana Torres", rol="CAJERO", ip="", user_agent="")


SIN_ESPECIFICAR = object()


class Escenario:
    def __init__(self, abierto=SIN_ESPECIFICAR, productos=None, metodos=None, ventas=None):
        # `abierto=None` significa "no hay caja abierta"; omitirlo, "usá una".
        self.caja = CajaRepoFake(turno() if abierto is SIN_ESPECIFICAR else abierto)
        self.stock = StockFake(productos if productos is not None else [vendible()])
        self.metodos = MetodoPagoRepoFake(metodos)
        self.ventas = VentaRepoFake(ventas)
        self.auditoria = AuditoriaFake()
        self.notificador = NotificadorFake()
        self.caso = RegistrarVentaUseCase(
            self.ventas, self.caja, self.stock, self.metodos,
            self.auditoria, self.notificador,
        )

    async def vender(self, items=None, pagos=None, **kwargs):
        datos = dict(
            items=items if items is not None else [(1, 2)],
            pagos=pagos if pagos is not None else [{"metodo": "EFECTIVO"}],
            **CTX,
        )
        datos.update(kwargs)
        return await self.caso.ejecutar(**datos)


class TestVentaExitosa:
    async def test_registra_la_venta_con_su_total(self):
        e = Escenario(turno(), [vendible(precio=Decimal("3.50"), stock=10)])
        v = await e.vender(items=[(1, 2)])
        assert v.id is not None
        assert v.total == Decimal("7.00")

    async def test_descuenta_el_stock(self):
        p = vendible(stock=10)
        e = Escenario(turno(), [p])
        await e.vender(items=[(1, 3)])
        assert p.stock == 7

    async def test_copia_nombre_y_precio_al_detalle(self):
        """Snapshot: el ticket no cambia si mañana sube el precio."""
        e = Escenario(turno(), [vendible(nombre="Galleta Soda", precio=Decimal("3.50"))])
        v = await e.vender(items=[(1, 1)])
        assert v.detalles[0].nombre == "Galleta Soda"
        assert v.detalles[0].precio_unitario == Decimal("3.50")

    async def test_guarda_el_nombre_del_vendedor(self):
        e = Escenario()
        v = await e.vender()
        assert v.vendedor == "Ana Torres"

    async def test_varios_productos_suman_al_total(self):
        e = Escenario(
            turno(),
            [
                vendible(id=1, precio=Decimal("3.00"), stock=10),
                vendible(id=2, precio=Decimal("2.50"), stock=10),
            ],
        )
        v = await e.vender(items=[(1, 2), (2, 4)])
        assert v.total == Decimal("16.00")  # 6 + 10

    async def test_queda_registrada_en_bitacora(self):
        e = Escenario()
        await e.vender()
        assert e.auditoria.eventos


class TestTurnoDeCaja:
    async def test_sin_turno_abierto_no_se_puede_vender(self):
        """La plata tiene que entrar a una caja concreta."""
        e = Escenario(abierto=None)
        with pytest.raises(ConflictoError):
            await e.vender()

    async def test_la_venta_queda_atada_al_turno_abierto(self):
        e = Escenario(turno(id=7))
        v = await e.vender()
        assert v.turno_id == 7

    async def test_un_turno_asignado_a_otro_cajero_lo_bloquea(self):
        """Si la admin le asignó el turno a alguien, otro no puede vender ahí."""
        e = Escenario(turno(asignado_a_id=99))
        with pytest.raises(ProhibidoError):
            await e.vender()

    async def test_el_cajero_asignado_si_puede_vender(self):
        e = Escenario(turno(asignado_a_id=2))
        v = await e.vender()
        assert v.id is not None

    async def test_no_descuenta_stock_si_no_hay_turno(self):
        p = vendible(stock=10)
        e = Escenario(abierto=None, productos=[p])
        with pytest.raises(ConflictoError):
            await e.vender()
        assert p.stock == 10


class TestValidacionDeItems:
    async def test_carrito_vacio(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.vender(items=[])

    @pytest.mark.parametrize("cantidad", [0, -1])
    async def test_cantidad_invalida(self, cantidad):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.vender(items=[(1, cantidad)])

    async def test_producto_inexistente(self):
        e = Escenario(turno(), [vendible(id=1)])
        with pytest.raises(NoEncontradoError):
            await e.vender(items=[(404, 1)])

    async def test_producto_inactivo(self):
        e = Escenario(turno(), [vendible(id=1, activo=False)])
        with pytest.raises(ValidacionError):
            await e.vender(items=[(1, 1)])

    async def test_stock_insuficiente(self):
        e = Escenario(turno(), [vendible(stock=2)])
        with pytest.raises(ConflictoError):
            await e.vender(items=[(1, 3)])

    async def test_el_stock_no_cambia_si_no_alcanza(self):
        p = vendible(stock=2)
        e = Escenario(turno(), [p])
        with pytest.raises(ConflictoError):
            await e.vender(items=[(1, 3)])
        assert p.stock == 2

    async def test_puede_vender_hasta_agotar(self):
        p = vendible(stock=5, stock_minimo=0)
        e = Escenario(turno(), [p])
        await e.vender(items=[(1, 5)])
        assert p.stock == 0


class TestPagos:
    async def test_sin_pagos_no_hay_venta(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.vender(pagos=[])

    async def test_un_solo_pago_sin_monto_cubre_el_total(self):
        """El caso más común del mostrador: 'todo en efectivo'."""
        e = Escenario(turno(), [vendible(precio=Decimal("3.50"))])
        v = await e.vender(items=[(1, 2)], pagos=[{"metodo": "EFECTIVO"}])
        assert v.pagos[0].monto == Decimal("7.00")

    async def test_metodo_de_pago_inexistente(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.vender(pagos=[{"metodo": "BITCOIN"}])

    async def test_metodo_de_pago_inactivo(self):
        from app.modules.modulo_c_ventas.domain.entities import MetodoPago

        e = Escenario(
            metodos=[
                MetodoPago(id=1, codigo="EFECTIVO", nombre="Efectivo",
                           es_efectivo=True, activo=True),
                MetodoPago(id=9, codigo="CHEQUE", nombre="Cheque",
                           es_efectivo=False, activo=False),
            ]
        )
        with pytest.raises(ValidacionError):
            await e.vender(pagos=[{"metodo": "CHEQUE"}])

    async def test_pago_de_monto_cero(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.vender(pagos=[{"metodo": "EFECTIVO", "monto": "0"}])

    async def test_venta_mixta_se_resume_como_MIXTO(self):
        """El resumen dice MIXTO; el desglose real vive en `pagos`, que es de
        donde salen los reportes por método."""
        e = Escenario(turno(), [vendible(precio=Decimal("5.00"))])
        v = await e.vender(
            items=[(1, 2)],
            pagos=[
                {"metodo": "EFECTIVO", "monto": "4.00"},
                {"metodo": "YAPE", "monto": "6.00"},
            ],
        )
        assert v.metodo_pago == "MIXTO"
        assert len(v.pagos) == 2

    async def test_una_venta_de_un_solo_metodo_lo_nombra(self):
        e = Escenario()
        v = await e.vender(pagos=[{"metodo": "YAPE"}])
        assert v.metodo_pago == "YAPE"

    async def test_el_vuelto_sale_del_efectivo_recibido(self):
        e = Escenario(turno(), [vendible(precio=Decimal("3.50"))])
        v = await e.vender(
            items=[(1, 2)],
            pagos=[{"metodo": "EFECTIVO", "monto_recibido": "20.00"}],
        )
        assert v.vuelto == Decimal("13.00")

    async def test_no_se_puede_recibir_menos_que_el_monto(self):
        e = Escenario(turno(), [vendible(precio=Decimal("10.00"))])
        with pytest.raises(ValidacionError):
            await e.vender(
                items=[(1, 1)],
                pagos=[{"metodo": "EFECTIVO", "monto": "10.00", "monto_recibido": "5.00"}],
            )

    async def test_en_pagos_digitales_se_ignora_el_monto_recibido(self):
        """Yape se paga por el importe exacto. Si el POS manda `monto_recibido`
        igual, se descarta en vez de generar un vuelto que nunca se entregó."""
        e = Escenario()
        v = await e.vender(pagos=[{"metodo": "YAPE", "monto_recibido": "50.00"}])
        assert v.pagos[0].monto_recibido is None
        assert v.vuelto == Decimal("0")


class TestVentaOffline:
    async def test_la_misma_venta_no_se_duplica_al_sincronizar(self):
        """El POS reintenta cuando vuelve la conexión: el uuid lo hace idempotente."""
        e = Escenario(turno(), [vendible(stock=10)])
        primera = await e.vender(items=[(1, 1)], client_uuid="uuid-1")
        segunda = await e.vender(items=[(1, 1)], client_uuid="uuid-1")
        assert primera.id == segunda.id
        assert len(e.ventas.ventas) == 1

    async def test_el_reintento_no_vuelve_a_descontar_stock(self):
        p = vendible(stock=10)
        e = Escenario(turno(), [p])
        await e.vender(items=[(1, 3)], client_uuid="uuid-1")
        await e.vender(items=[(1, 3)], client_uuid="uuid-1")
        assert p.stock == 7, "el segundo envío no debe descontar de nuevo"

    async def test_dos_ventas_distintas_con_uuids_distintos_si_entran(self):
        e = Escenario(turno(), [vendible(stock=10)])
        await e.vender(items=[(1, 1)], client_uuid="uuid-1")
        await e.vender(items=[(1, 1)], client_uuid="uuid-2")
        assert len(e.ventas.ventas) == 2

    async def test_marca_las_ventas_registradas_offline(self):
        e = Escenario()
        v = await e.vender(client_uuid="uuid-9", registrada_offline=True)
        assert v.registrada_offline is True


class TestAlertaDeStockBajo:
    async def test_avisa_si_la_venta_deja_el_producto_en_su_minimo(self):
        e = Escenario(turno(), [vendible(stock=3, stock_minimo=2)])
        await e.vender(items=[(1, 1)])  # queda en 2 == mínimo
        assert "STOCK_BAJO" in e.notificador.tipos()

    async def test_no_avisa_si_queda_por_encima(self):
        e = Escenario(turno(), [vendible(stock=10, stock_minimo=2)])
        await e.vender(items=[(1, 1)])
        assert e.notificador.avisos == []

    async def test_no_repite_el_aviso(self):
        e = Escenario(turno(), [vendible(stock=4, stock_minimo=2)])
        await e.vender(items=[(1, 2)])  # queda en 2: avisa
        await e.vender(items=[(1, 1)])  # queda en 1: ya avisó
        assert e.notificador.tipos().count("STOCK_BAJO") == 1

    async def test_la_venta_funciona_sin_notificador(self):
        caso = RegistrarVentaUseCase(
            VentaRepoFake(), CajaRepoFake(turno()), StockFake([vendible()]),
            MetodoPagoRepoFake(), AuditoriaFake(), None,
        )
        v = await caso.ejecutar(items=[(1, 1)], pagos=[{"metodo": "EFECTIVO"}], **CTX)
        assert v.id is not None
