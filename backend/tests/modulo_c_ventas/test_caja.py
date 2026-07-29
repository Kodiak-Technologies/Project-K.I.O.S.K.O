"""Apertura y cierre de caja, con su arqueo.

La regla más importante del cierre es que **un descuadre sin explicación no se
puede cerrar**: si falta o sobra plata, el cajero tiene que escribir por qué, y
eso queda para la administradora.

Y sólo puede haber un turno abierto a la vez: si no, no se sabría a qué caja
entró cada venta.
"""

from decimal import Decimal

import pytest

from app.modules.modulo_c_ventas.application.abrir_caja_usecase import (
    AbrirCajaUseCase,
)
from app.modules.modulo_c_ventas.application.cerrar_caja_usecase import (
    CerrarCajaUseCase,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    ProhibidoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    CajaRepoFake,
    NotificadorFake,
    turno,
)

CTX = dict(usuario_id=2, nombre_usuario="Ana Torres", rol="CAJERO", ip="", user_agent="")
SIN_ESPECIFICAR = object()


class TestAbrirCaja:
    def _caso(self, abierto=None):
        caja = CajaRepoFake(abierto)
        aud = AuditoriaFake()
        noti = NotificadorFake()
        return AbrirCajaUseCase(caja, aud, noti), caja, aud, noti

    async def test_abre_con_el_efectivo_contado(self):
        caso, _, _, _ = self._caso()
        t = await caso.ejecutar(monto_inicial=Decimal("150.50"), **CTX)
        assert t.id is not None
        assert t.monto_inicial == Decimal("150.50")
        assert t.esta_abierto() is True

    async def test_guarda_quien_abrio(self):
        caso, _, _, _ = self._caso()
        t = await caso.ejecutar(monto_inicial=Decimal("100"), **CTX)
        assert t.usuario_id == 2
        assert t.abierto_por == "Ana Torres"

    async def test_puede_abrir_con_caja_vacia(self):
        """Arrancar sin sencillo es válido."""
        caso, _, _, _ = self._caso()
        t = await caso.ejecutar(monto_inicial=Decimal("0"), **CTX)
        assert t.monto_inicial == Decimal("0")

    async def test_no_se_puede_abrir_si_ya_hay_uno_abierto(self):
        """Con dos turnos abiertos no se sabría a qué caja entra cada venta."""
        caso, _, _, _ = self._caso(abierto=turno())
        with pytest.raises(ConflictoError):
            await caso.ejecutar(monto_inicial=Decimal("100"), **CTX)

    async def test_monto_inicial_negativo(self):
        caso, _, _, _ = self._caso()
        with pytest.raises(ValidacionError):
            await caso.ejecutar(monto_inicial=Decimal("-1"), **CTX)

    async def test_queda_registrado_en_bitacora(self):
        caso, _, aud, _ = self._caso()
        await caso.ejecutar(monto_inicial=Decimal("100"), **CTX)
        assert aud.eventos

    async def test_avisa_a_la_administradora(self):
        caso, _, _, noti = self._caso()
        await caso.ejecutar(monto_inicial=Decimal("100"), **CTX)
        assert "APERTURA_CAJA" in noti.tipos()

    async def test_funciona_sin_notificador(self):
        caso = AbrirCajaUseCase(CajaRepoFake(), AuditoriaFake(), None)
        t = await caso.ejecutar(monto_inicial=Decimal("100"), **CTX)
        assert t.id is not None


class TestCerrarCaja:
    def _caso(self, abierto=SIN_ESPECIFICAR, esperado=Decimal("100"), vendido=Decimal("0")):
        caja = CajaRepoFake(turno() if abierto is SIN_ESPECIFICAR else abierto)
        # `efectivo_esperado` = monto inicial (100) + ventas en efectivo
        # - devoluciones en efectivo.
        caja.totales = {
            "ventas_efectivo": esperado - Decimal("100"),
            "devoluciones_efectivo": Decimal("0"),
            "totales_por_metodo": {},
            "total_vendido": vendido,
            "numero_ventas": 0,
        }
        aud = AuditoriaFake()
        noti = NotificadorFake()
        return CerrarCajaUseCase(caja, aud, noti), caja, aud, noti

    async def test_cierra_cuando_cuadra(self):
        caso, caja, _, _ = self._caso(esperado=Decimal("100"))
        _, arqueo = await caso.ejecutar(monto_final=Decimal("100"), **CTX)
        assert arqueo.cuadrado is True
        assert arqueo.diferencia == Decimal("0")

    async def test_el_turno_queda_cerrado(self):
        caso, caja, _, _ = self._caso()
        await caso.ejecutar(monto_final=Decimal("100"), **CTX)
        assert await caja.turno_abierto() is None

    async def test_guarda_el_arqueo(self):
        caso, caja, _, _ = self._caso()
        await caso.ejecutar(monto_final=Decimal("100"), **CTX)
        assert len(caja.arqueos) == 1

    async def test_un_faltante_sin_explicacion_no_deja_cerrar(self):
        """La administradora tiene que poder saber qué pasó con la plata."""
        caso, _, _, _ = self._caso(esperado=Decimal("100"))
        with pytest.raises(ValidacionError):
            await caso.ejecutar(monto_final=Decimal("90"), **CTX)

    async def test_un_sobrante_sin_explicacion_tampoco(self):
        caso, _, _, _ = self._caso(esperado=Decimal("100"))
        with pytest.raises(ValidacionError):
            await caso.ejecutar(monto_final=Decimal("110"), **CTX)

    async def test_con_comentario_si_deja_cerrar_descuadrado(self):
        caso, _, _, _ = self._caso(esperado=Decimal("100"))
        _, arqueo = await caso.ejecutar(
            monto_final=Decimal("90"),
            comentario="Se pagó un delivery de la caja",
            **CTX,
        )
        assert arqueo.diferencia == Decimal("-10")
        assert arqueo.comentario == "Se pagó un delivery de la caja"

    async def test_un_comentario_en_blanco_no_cuenta_como_explicacion(self):
        caso, _, _, _ = self._caso(esperado=Decimal("100"))
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                monto_final=Decimal("90"), comentario="   ", **CTX
            )

    async def test_el_error_dice_cuanto_falta(self):
        caso, _, _, _ = self._caso(esperado=Decimal("100"))
        with pytest.raises(ValidacionError) as err:
            await caso.ejecutar(monto_final=Decimal("90"), **CTX)
        assert "faltan" in str(err.value).lower()

    async def test_el_error_distingue_sobrante_de_faltante(self):
        caso, _, _, _ = self._caso(esperado=Decimal("100"))
        with pytest.raises(ValidacionError) as err:
            await caso.ejecutar(monto_final=Decimal("110"), **CTX)
        assert "sobran" in str(err.value).lower()

    async def test_sin_turno_abierto_no_hay_nada_que_cerrar(self):
        caso, _, _, _ = self._caso(abierto=None)
        with pytest.raises(ConflictoError):
            await caso.ejecutar(monto_final=Decimal("100"), **CTX)

    async def test_un_turno_asignado_a_otro_no_lo_puede_cerrar(self):
        caso, _, _, _ = self._caso(abierto=turno(asignado_a_id=99))
        with pytest.raises(ProhibidoError):
            await caso.ejecutar(monto_final=Decimal("100"), **CTX)

    async def test_el_admin_puede_cerrar_un_turno_ajeno(self):
        """Si el cajero se fue sin cerrar, alguien tiene que poder hacerlo."""
        caso, _, _, _ = self._caso(abierto=turno(asignado_a_id=99))
        datos = {**CTX, "rol": "ADMIN"}
        t, _ = await caso.ejecutar(monto_final=Decimal("100"), **datos)
        assert t is not None

    async def test_avisa_del_cierre(self):
        caso, _, _, noti = self._caso()
        await caso.ejecutar(monto_final=Decimal("100"), **CTX)
        assert "CIERRE_CAJA" in noti.tipos()

    async def test_el_arqueo_guarda_lo_vendido_y_lo_esperado(self):
        caso, _, _, _ = self._caso(esperado=Decimal("250"), vendido=Decimal("150"))
        _, arqueo = await caso.ejecutar(
            monto_final=Decimal("250"), **CTX
        )
        assert arqueo.efectivo_esperado == Decimal("250")
        assert arqueo.efectivo_contado == Decimal("250")
        assert arqueo.total_vendido == Decimal("150")
