"""Proveedores: alta, compras a crédito y pagos.

La deuda es un saldo denormalizado que se mueve con cada operación, así que las
reglas apuntan a que no se desincronice ni quede en un estado imposible:
  - una compra a crédito suma, un pago resta;
  - no se puede pagar más de lo que se debe (la deuda no queda negativa);
  - a un proveedor inactivo no se le compran cosas nuevas, pero SÍ se le puede
    pagar lo que ya se le debe.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.crear_proveedor_usecase import (
    CrearProveedorUseCase,
)
from app.modules.modulo_b_inventario.application.registrar_compra_credito_usecase import (
    RegistrarCompraCreditoUseCase,
)
from app.modules.modulo_b_inventario.application.registrar_pago_proveedor_usecase import (
    RegistrarPagoProveedorUseCase,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    PagoProveedorRepoFake,
    ProveedorRepoFake,
    SolicitudRepoFake,
    proveedor,
)

CTX = dict(usuario_id=1, usuario_nombre="Admin", ip="", user_agent="")
HOY = date(2026, 7, 27)


class TestCrearProveedor:
    def _caso(self, existentes=None):
        repo = ProveedorRepoFake(existentes or [])
        aud = AuditoriaFake()
        return CrearProveedorUseCase(repo, aud), repo, aud

    async def test_crea_con_los_datos_minimos(self):
        caso, _, _ = self._caso()
        p = await caso.ejecutar(
            razon_social="Distribuidora Andina", ruc=None, telefono=None,
            email=None, direccion=None, **CTX,
        )
        assert p.id is not None
        assert p.razon_social == "Distribuidora Andina"

    async def test_nace_sin_deuda(self):
        caso, _, _ = self._caso()
        p = await caso.ejecutar(
            razon_social="X", ruc=None, telefono=None, email=None,
            direccion=None, **CTX,
        )
        assert p.deuda_actual == Decimal("0")
        assert p.tiene_deuda() is False

    @pytest.mark.parametrize("razon", ["", "   "])
    async def test_razon_social_obligatoria(self, razon):
        caso, _, _ = self._caso()
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                razon_social=razon, ruc=None, telefono=None, email=None,
                direccion=None, **CTX,
            )

    async def test_ruc_duplicado(self):
        """El RUC identifica al proveedor: dos con el mismo serían el mismo."""
        caso, _, _ = self._caso([proveedor(id=1, ruc="20481234567")])
        with pytest.raises(ConflictoError):
            await caso.ejecutar(
                razon_social="Otra", ruc="20481234567", telefono=None,
                email=None, direccion=None, **CTX,
            )

    async def test_el_ruc_es_opcional(self):
        """Un proveedor informal del mercado puede no tener RUC."""
        caso, _, _ = self._caso()
        p = await caso.ejecutar(
            razon_social="Casero del mercado", ruc=None, telefono=None,
            email=None, direccion=None, **CTX,
        )
        assert p.ruc is None

    async def test_dos_sin_ruc_no_chocan(self):
        caso, _, _ = self._caso([proveedor(id=1, ruc=None)])
        p = await caso.ejecutar(
            razon_social="Otro sin RUC", ruc=None, telefono=None,
            email=None, direccion=None, **CTX,
        )
        assert p.id is not None


class EscenarioDeuda:
    def __init__(self, proveedores=None, solicitudes=None):
        self.proveedores = ProveedorRepoFake(
            proveedores if proveedores is not None else [proveedor(id=1)]
        )
        self.pagos = PagoProveedorRepoFake()
        self.solicitudes = SolicitudRepoFake(solicitudes or [])
        self.auditoria = AuditoriaFake()
        self.compra = RegistrarCompraCreditoUseCase(
            self.proveedores, self.pagos, self.solicitudes, self.auditoria
        )
        self.pago = RegistrarPagoProveedorUseCase(
            self.proveedores, self.pagos, self.auditoria
        )


class TestCompraACredito:
    async def test_suma_a_la_deuda(self):
        p = proveedor(id=1, deuda_actual=Decimal("100"))
        e = EscenarioDeuda([p])
        await e.compra.ejecutar(
            proveedor_id=1, monto=Decimal("50"), fecha=HOY,
            concepto="Ingreso #5", solicitud_ingreso_id=None, **CTX,
        )
        assert p.deuda_actual == Decimal("150")

    async def test_registra_el_movimiento_como_compra(self):
        e = EscenarioDeuda()
        await e.compra.ejecutar(
            proveedor_id=1, monto=Decimal("50"), fecha=HOY,
            concepto=None, solicitud_ingreso_id=None, **CTX,
        )
        assert e.pagos.tipos() == ["compra_credito"]

    @pytest.mark.parametrize("monto", [Decimal("0"), Decimal("-1")])
    async def test_el_monto_debe_ser_positivo(self, monto):
        e = EscenarioDeuda()
        with pytest.raises(ValidacionError):
            await e.compra.ejecutar(
                proveedor_id=1, monto=monto, fecha=HOY,
                concepto=None, solicitud_ingreso_id=None, **CTX,
            )

    async def test_proveedor_inexistente(self):
        e = EscenarioDeuda([])
        with pytest.raises(NoEncontradoError):
            await e.compra.ejecutar(
                proveedor_id=404, monto=Decimal("10"), fecha=HOY,
                concepto=None, solicitud_ingreso_id=None, **CTX,
            )

    async def test_no_se_le_compra_a_un_proveedor_inactivo(self):
        """Dar de baja a un proveedor tiene que impedir seguir comprándole."""
        e = EscenarioDeuda([proveedor(id=1, activo=False)])
        with pytest.raises(ValidacionError):
            await e.compra.ejecutar(
                proveedor_id=1, monto=Decimal("10"), fecha=HOY,
                concepto=None, solicitud_ingreso_id=None, **CTX,
            )

    async def test_la_deuda_no_cambia_si_falla(self):
        p = proveedor(id=1, deuda_actual=Decimal("100"))
        e = EscenarioDeuda([p])
        with pytest.raises(ValidacionError):
            await e.compra.ejecutar(
                proveedor_id=1, monto=Decimal("0"), fecha=HOY,
                concepto=None, solicitud_ingreso_id=None, **CTX,
            )
        assert p.deuda_actual == Decimal("100")

    async def test_solicitud_de_ingreso_inexistente(self):
        e = EscenarioDeuda()
        with pytest.raises(NoEncontradoError):
            await e.compra.ejecutar(
                proveedor_id=1, monto=Decimal("10"), fecha=HOY,
                concepto=None, solicitud_ingreso_id=404, **CTX,
            )


class TestPagoAProveedor:
    async def test_resta_de_la_deuda(self):
        p = proveedor(id=1, deuda_actual=Decimal("100"))
        e = EscenarioDeuda([p])
        await e.pago.ejecutar(
            proveedor_id=1, monto=Decimal("40"), fecha=HOY, concepto=None, **CTX
        )
        assert p.deuda_actual == Decimal("60")

    async def test_puede_saldar_la_deuda_completa(self):
        p = proveedor(id=1, deuda_actual=Decimal("100"))
        e = EscenarioDeuda([p])
        await e.pago.ejecutar(
            proveedor_id=1, monto=Decimal("100"), fecha=HOY, concepto=None, **CTX
        )
        assert p.deuda_actual == Decimal("0")
        assert p.tiene_deuda() is False

    async def test_no_se_puede_pagar_mas_de_lo_que_se_debe(self):
        """Sería un saldo a favor, que el sistema no maneja: es un error de carga."""
        p = proveedor(id=1, deuda_actual=Decimal("100"))
        e = EscenarioDeuda([p])
        with pytest.raises(ValidacionError):
            await e.pago.ejecutar(
                proveedor_id=1, monto=Decimal("100.01"), fecha=HOY,
                concepto=None, **CTX,
            )

    async def test_no_se_puede_pagar_sin_deuda(self):
        e = EscenarioDeuda([proveedor(id=1, deuda_actual=Decimal("0"))])
        with pytest.raises(ValidacionError):
            await e.pago.ejecutar(
                proveedor_id=1, monto=Decimal("1"), fecha=HOY, concepto=None, **CTX
            )

    async def test_registra_el_movimiento_como_pago(self):
        e = EscenarioDeuda([proveedor(id=1, deuda_actual=Decimal("100"))])
        await e.pago.ejecutar(
            proveedor_id=1, monto=Decimal("10"), fecha=HOY, concepto=None, **CTX
        )
        assert e.pagos.tipos() == ["pago"]

    async def test_a_un_proveedor_inactivo_SI_se_le_puede_pagar(self):
        """Se le dejó de comprar, pero la deuda vieja hay que poder saldarla."""
        p = proveedor(id=1, activo=False, deuda_actual=Decimal("100"))
        e = EscenarioDeuda([p])
        await e.pago.ejecutar(
            proveedor_id=1, monto=Decimal("100"), fecha=HOY, concepto=None, **CTX
        )
        assert p.deuda_actual == Decimal("0")

    @pytest.mark.parametrize("monto", [Decimal("0"), Decimal("-5")])
    async def test_el_monto_debe_ser_positivo(self, monto):
        e = EscenarioDeuda([proveedor(id=1, deuda_actual=Decimal("100"))])
        with pytest.raises(ValidacionError):
            await e.pago.ejecutar(
                proveedor_id=1, monto=monto, fecha=HOY, concepto=None, **CTX
            )

    async def test_proveedor_inexistente(self):
        e = EscenarioDeuda([])
        with pytest.raises(NoEncontradoError):
            await e.pago.ejecutar(
                proveedor_id=404, monto=Decimal("10"), fecha=HOY,
                concepto=None, **CTX,
            )

    async def test_fecha_con_formato_invalido(self):
        e = EscenarioDeuda([proveedor(id=1, deuda_actual=Decimal("100"))])
        with pytest.raises(ValidacionError):
            await e.pago.ejecutar(
                proveedor_id=1, monto=Decimal("10"), fecha="27-07-2026",
                concepto=None, **CTX,
            )


class TestCicloCompletoDeDeuda:
    async def test_compras_y_pagos_dejan_el_saldo_correcto(self):
        """La deuda es un saldo denormalizado: tiene que cuadrar tras varias
        operaciones seguidas."""
        p = proveedor(id=1, deuda_actual=Decimal("0"))
        e = EscenarioDeuda([p])
        await e.compra.ejecutar(
            proveedor_id=1, monto=Decimal("300"), fecha=HOY,
            concepto=None, solicitud_ingreso_id=None, **CTX,
        )
        await e.compra.ejecutar(
            proveedor_id=1, monto=Decimal("150.50"), fecha=HOY,
            concepto=None, solicitud_ingreso_id=None, **CTX,
        )
        await e.pago.ejecutar(
            proveedor_id=1, monto=Decimal("200"), fecha=HOY, concepto=None, **CTX
        )
        assert p.deuda_actual == Decimal("250.50")
        assert len(e.pagos.pagos) == 3
