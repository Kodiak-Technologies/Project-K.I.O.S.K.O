"""`CambiarPrecioUseCase`: precios de venta y compra, con historial.

Reglas en juego:
  - un producto a la venta nunca puede valer 0 (mismo criterio que el alta);
  - cada cambio REAL deja una fila en `historial_precios`, que es append-only;
  - reescribir el mismo importe no es un cambio y no ensucia el histórico.
"""

from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.cambiar_precio_usecase import (
    CambiarPrecioUseCase,
)
from app.shared.kernel.exceptions import ValidacionError

from .dobles import (
    AuditoriaFake,
    HistorialPrecioRepoFake,
    ProductoRepoFake,
    producto,
)

CTX = dict(usuario_id=1, usuario_nombre="Admin", ip="", user_agent="")


class Escenario:
    def __init__(self, productos=None):
        self.productos = ProductoRepoFake(
            productos
            if productos is not None
            else [producto(precio=Decimal("3.50"), precio_compra_actual=Decimal("2.60"))]
        )
        self.historial = HistorialPrecioRepoFake()
        self.auditoria = AuditoriaFake()
        self.caso = CambiarPrecioUseCase(
            self.productos, self.historial, self.auditoria
        )

    async def cambiar(self, venta=None, compra=None, producto_id=1):
        return await self.caso.ejecutar(
            producto_id=producto_id,
            precio_venta=venta,
            precio_compra_actual=compra,
            **CTX,
        )


class TestCambioValido:
    async def test_cambia_el_precio_de_venta(self):
        e = Escenario()
        p, hubo_historial, filas = await e.cambiar(venta=Decimal("4.00"))
        assert p.precio == Decimal("4.00")
        assert hubo_historial is True
        assert len(filas) == 1

    async def test_cambia_el_precio_de_compra(self):
        e = Escenario()
        p, _, filas = await e.cambiar(compra=Decimal("3.00"))
        assert p.precio_compra_actual == Decimal("3.00")
        assert [str(f.tipo_precio) for f in filas] == ["compra"]

    async def test_cambiar_los_dos_genera_dos_filas_de_historial(self):
        e = Escenario()
        _, _, filas = await e.cambiar(venta=Decimal("4.00"), compra=Decimal("3.00"))
        assert sorted(str(f.tipo_precio) for f in filas) == ["compra", "venta"]

    async def test_el_historial_guarda_el_precio_anterior(self):
        """Sin el 'antes' el historial no sirve para ver la evolución."""
        e = Escenario()
        _, _, filas = await e.cambiar(venta=Decimal("4.00"))
        assert filas[0].precio_anterior == Decimal("3.50")
        assert filas[0].precio_nuevo == Decimal("4.00")

    async def test_registra_quien_lo_cambio(self):
        e = Escenario()
        _, _, filas = await e.cambiar(venta=Decimal("4.00"))
        assert filas[0].modificado_por == 1
        assert filas[0].modificado_por_nombre == "Admin"

    async def test_reescribir_el_mismo_precio_no_genera_historial(self):
        """Guardar sin tocar nada no es un cambio de precio."""
        e = Escenario()
        p, hubo_historial, filas = await e.cambiar(venta=Decimal("3.50"))
        assert hubo_historial is False
        assert filas == []
        assert p.precio == Decimal("3.50")

    async def test_sin_cambio_real_tampoco_se_audita(self):
        e = Escenario()
        await e.cambiar(venta=Decimal("3.50"))
        assert e.auditoria.eventos == []

    async def test_un_cambio_real_si_se_audita(self):
        e = Escenario()
        await e.cambiar(venta=Decimal("4.00"))
        assert e.auditoria.acciones() == ["cambiar_precio"]

    async def test_el_precio_de_compra_si_puede_ser_cero(self):
        """A diferencia del de venta: un obsequio del proveedor cuesta 0."""
        e = Escenario()
        p, _, _ = await e.cambiar(compra=Decimal("0"))
        assert p.precio_compra_actual == Decimal("0")

    async def test_acepta_el_precio_como_float_o_string(self):
        """El router puede mandar cualquiera de los dos; el caso de uso
        normaliza a Decimal antes de comparar."""
        e = Escenario()
        p, _, _ = await e.cambiar(venta=4.25)
        assert p.precio == Decimal("4.25")


class TestCambioRechazado:
    async def test_no_mandar_ningun_precio(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.cambiar()

    @pytest.mark.parametrize("valor", [Decimal("0"), Decimal("-1"), Decimal("-0.01")])
    async def test_precio_de_venta_menor_o_igual_a_cero(self, valor):
        """Un producto a la venta no puede valer 0 (HU-B01)."""
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.cambiar(venta=valor)

    async def test_precio_de_compra_negativo(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.cambiar(compra=Decimal("-1"))

    async def test_el_precio_no_cambia_si_la_validacion_falla(self):
        p = producto(precio=Decimal("3.50"))
        e = Escenario([p])
        with pytest.raises(ValidacionError):
            await e.cambiar(venta=Decimal("0"))
        assert p.precio == Decimal("3.50")

    async def test_no_registra_historial_si_la_validacion_falla(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.cambiar(venta=Decimal("-5"))
        assert e.historial.filas == []
