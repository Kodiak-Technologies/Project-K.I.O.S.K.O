"""`AjustarStockUseCase`: la corrección manual de stock (solo ADMIN).

Es el reemplazo del flujo de mermas. Lo que se juega acá:
  - el stock NUNCA queda negativo (el descuento es atómico);
  - todo ajuste deja motivo y asiento en `movimientos_inventario`, porque es la
    única trazabilidad del faltante;
  - si el ajuste deja el producto bajo mínimo, se avisa una sola vez.
"""

import pytest

from app.modules.modulo_b_inventario.application.ajustar_stock_usecase import (
    AjustarStockUseCase,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    MovimientoRepoFake,
    NotificadorFake,
    ProductoRepoFake,
    producto,
)

CTX = dict(usuario_id=1, usuario_nombre="Admin", ip="1.2.3.4", user_agent="tests")


class Escenario:
    def __init__(self, productos=None):
        self.productos = ProductoRepoFake(
            productos if productos is not None else [producto()]
        )
        self.movimientos = MovimientoRepoFake()
        self.auditoria = AuditoriaFake()
        self.notificador = NotificadorFake()
        self.caso = AjustarStockUseCase(
            self.productos, self.movimientos, self.auditoria, self.notificador
        )

    async def ajustar(self, delta, motivo="conteo físico", producto_id=1):
        return await self.caso.ejecutar(
            producto_id=producto_id, delta=delta, motivo=motivo, **CTX
        )


class TestAjusteValido:
    async def test_sumar_incrementa_el_stock(self):
        e = Escenario([producto(stock=10)])
        r = await e.ajustar(+5)
        assert r.stock_anterior == 10
        assert r.stock_actual == 15
        assert r.delta == 5

    async def test_restar_descuenta(self):
        e = Escenario([producto(stock=10)])
        r = await e.ajustar(-4)
        assert r.stock_actual == 6

    async def test_puede_dejar_el_stock_exactamente_en_cero(self):
        e = Escenario([producto(stock=10)])
        r = await e.ajustar(-10)
        assert r.stock_actual == 0

    async def test_deja_asiento_de_tipo_ajuste(self):
        e = Escenario([producto(stock=10)])
        await e.ajustar(-3)
        assert e.movimientos.tipos() == ["ajuste"]

    async def test_el_asiento_guarda_el_motivo(self):
        """Es la única trazabilidad de por qué faltaban unidades."""
        e = Escenario([producto(stock=10)])
        await e.ajustar(-3, motivo="se rompieron 3 botellas")
        assert e.movimientos.movimientos[0].motivo == "se rompieron 3 botellas"

    async def test_el_asiento_conserva_el_signo_del_ajuste(self):
        e = Escenario([producto(stock=10)])
        await e.ajustar(-3)
        assert e.movimientos.movimientos[0].cantidad == -3

    async def test_queda_registrado_en_bitacora(self):
        e = Escenario([producto(stock=10)])
        await e.ajustar(-3)
        assert e.auditoria.eventos, "el ajuste manual debe auditarse"


class TestAjusteRechazado:
    async def test_delta_cero_no_tiene_sentido(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.ajustar(0)

    @pytest.mark.parametrize("motivo", ["", "  ", "ab"])
    async def test_motivo_vacio_o_muy_corto(self, motivo):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.ajustar(-1, motivo=motivo)

    async def test_motivo_demasiado_largo(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.ajustar(-1, motivo="x" * 201)

    async def test_el_motivo_se_recorta_antes_de_medirlo(self):
        """'  ok  ' tiene 6 caracteres pero sólo 2 útiles."""
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.ajustar(-1, motivo="  ab  ")

    async def test_producto_inexistente(self):
        e = Escenario([])
        with pytest.raises(NoEncontradoError):
            await e.ajustar(-1)

    async def test_producto_eliminado(self):
        from datetime import datetime, timezone

        e = Escenario([producto(deleted_at=datetime.now(timezone.utc))])
        with pytest.raises(NoEncontradoError):
            await e.ajustar(-1)

    async def test_no_se_puede_descontar_mas_de_lo_que_hay(self):
        """El stock nunca queda negativo: el descuento es atómico."""
        e = Escenario([producto(stock=5)])
        with pytest.raises(ConflictoError):
            await e.ajustar(-6)

    async def test_el_stock_queda_intacto_si_no_alcanza(self):
        p = producto(stock=5)
        e = Escenario([p])
        with pytest.raises(ConflictoError):
            await e.ajustar(-6)
        assert p.stock == 5

    async def test_no_deja_asiento_si_el_ajuste_falla(self):
        """Un movimiento sin efecto real ensuciaría la bitácora de inventario."""
        e = Escenario([producto(stock=5)])
        with pytest.raises(ConflictoError):
            await e.ajustar(-6)
        assert e.movimientos.movimientos == []

    async def test_el_error_dice_cuanto_hay_disponible(self):
        e = Escenario([producto(stock=5)])
        with pytest.raises(ConflictoError) as err:
            await e.ajustar(-6)
        assert "5" in str(err.value)

    async def test_nada_se_valida_despues_de_tocar_el_stock(self):
        """Las validaciones van antes del UPDATE: si el motivo es inválido, el
        stock no se toca."""
        p = producto(stock=10)
        e = Escenario([p])
        with pytest.raises(ValidacionError):
            await e.ajustar(-3, motivo="")
        assert p.stock == 10


class TestAlertaDeStockMinimo:
    async def test_avisa_cuando_el_ajuste_deja_el_producto_en_el_minimo(self):
        e = Escenario([producto(stock=10, stock_minimo=5)])
        await e.ajustar(-5)  # queda en 5 == mínimo
        assert "STOCK_BAJO" in e.notificador.tipos()

    async def test_no_avisa_si_queda_por_encima_del_minimo(self):
        e = Escenario([producto(stock=10, stock_minimo=5)])
        await e.ajustar(-1)  # queda en 9
        assert e.notificador.avisos == []

    async def test_no_repite_el_aviso(self):
        """La alerta es única por producto hasta que se reponga (HU-B13)."""
        e = Escenario([producto(stock=10, stock_minimo=5)])
        await e.ajustar(-5)
        await e.ajustar(-1)
        assert e.notificador.tipos().count("STOCK_BAJO") == 1

    async def test_al_reponer_por_encima_del_minimo_la_alerta_se_rearma(self):
        e = Escenario([producto(stock=10, stock_minimo=5)])
        await e.ajustar(-5)  # avisa
        await e.ajustar(+10)  # repone: se rearma
        await e.ajustar(-10)  # vuelve a bajar: avisa de nuevo
        assert e.notificador.tipos().count("STOCK_BAJO") == 2

    async def test_sin_umbral_definido_no_avisa_nunca(self):
        e = Escenario([producto(stock=10, stock_minimo=0)])
        await e.ajustar(-10)
        assert e.notificador.avisos == []

    async def test_el_ajuste_funciona_aunque_no_haya_notificador(self):
        """El notificador es opcional: su ausencia no puede romper la operación."""
        productos = ProductoRepoFake([producto(stock=10, stock_minimo=5)])
        caso = AjustarStockUseCase(
            productos, MovimientoRepoFake(), AuditoriaFake(), None
        )
        r = await caso.ejecutar(producto_id=1, delta=-5, motivo="conteo", **CTX)
        assert r.stock_actual == 5
