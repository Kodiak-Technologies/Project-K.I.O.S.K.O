"""Dominio del Módulo B: value objects y entidades.

Acá viven las reglas de inventario que no dependen de la BD: cuándo un producto
se puede vender, cuándo hay que reponerlo, qué transiciones acepta una solicitud
de ingreso y cómo se mueve la deuda de un proveedor.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.domain.entities import (
    MovimientoInventario,
    PagoProveedor,
    Producto,
    Proveedor,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.value_objects import (
    CodigoInterno,
    EstadoSolicitud,
    TipoMovimiento,
    TipoPago,
    TipoPrecio,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    ValidacionError,
)

AHORA = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def producto(**kwargs) -> Producto:
    base = dict(
        id=1,
        codigo="7750000000014",
        nombre="Galleta Soda",
        categoria_id=1,
        precio=Decimal("3.50"),
    )
    base.update(kwargs)
    return Producto(**base)  # type: ignore[arg-type]


def proveedor(**kwargs) -> Proveedor:
    base = dict(
        id=1, razon_social="Distribuidora Andina", creado_por=1, creado_por_nombre="Admin"
    )
    base.update(kwargs)
    return Proveedor(**base)  # type: ignore[arg-type]


def solicitud(**kwargs) -> SolicitudIngreso:
    base = dict(
        id=1,
        estado=EstadoSolicitud(EstadoSolicitud.PENDIENTE),
        proveedor_id=1,
        foto_boleta_url="https://drive/x.png",
        solicitado_por=2,
        solicitado_por_nombre="Cajero",
    )
    base.update(kwargs)
    return SolicitudIngreso(**base)  # type: ignore[arg-type]


# =============================================================================
# Value objects
# =============================================================================


class TestCatalogosCerrados:
    @pytest.mark.parametrize("valor", ["Pendiente", "Aprobada", "Rechazada"])
    def test_estado_solicitud_acepta_los_suyos(self, valor):
        assert str(EstadoSolicitud(valor)) == valor

    @pytest.mark.parametrize("valor", ["pendiente", "APROBADA", "Anulada", ""])
    def test_estado_solicitud_rechaza_el_resto(self, valor):
        with pytest.raises(ValidacionError):
            EstadoSolicitud(valor)

    @pytest.mark.parametrize("valor", ["ingreso", "ajuste", "venta", "devolucion"])
    def test_tipo_movimiento_acepta_los_cuatro_vigentes(self, valor):
        assert str(TipoMovimiento(valor)) == valor

    def test_tipo_movimiento_ya_no_acepta_merma(self):
        """El flujo de mermas se eliminó: su reemplazo es el ajuste manual."""
        with pytest.raises(ValidacionError):
            TipoMovimiento("merma")

    @pytest.mark.parametrize("valor", ["compra_credito", "pago"])
    def test_tipo_pago(self, valor):
        assert str(TipoPago(valor)) == valor

    @pytest.mark.parametrize("valor", ["venta", "compra"])
    def test_tipo_precio(self, valor):
        assert str(TipoPrecio(valor)) == valor

    def test_el_mensaje_de_error_lista_los_permitidos(self):
        """Quien lo reciba tiene que saber qué sí puede mandar."""
        with pytest.raises(ValidacionError) as e:
            TipoPago("efectivo")
        assert "compra_credito" in str(e.value) and "pago" in str(e.value)


class TestCodigoInterno:
    @pytest.mark.parametrize("valor", ["PAP-001", "AB-123", "ABCDE-123456"])
    def test_acepta_el_formato_prefijo_correlativo(self, valor):
        assert str(CodigoInterno(valor)) == valor

    @pytest.mark.parametrize(
        "valor,motivo",
        [
            ("pap-001", "prefijo en minúsculas"),
            ("P-001", "prefijo de 1 letra"),
            ("ABCDEF-001", "prefijo de 6 letras"),
            ("PAP-01", "correlativo de 2 dígitos"),
            ("PAP-1234567", "correlativo de 7 dígitos"),
            ("PAP001", "sin guion"),
            ("PAP-ABC", "correlativo no numérico"),
            ("", "vacío"),
        ],
    )
    def test_rechaza_lo_que_no_cumple(self, valor, motivo):
        with pytest.raises(ValidacionError):
            CodigoInterno(valor)


# =============================================================================
# Producto
# =============================================================================


class TestProductoDisponibleParaVenta:
    def test_activo_con_stock_se_vende(self):
        assert producto(stock=5).disponible_para_venta() is True

    def test_sin_stock_no_se_vende(self):
        assert producto(stock=0).disponible_para_venta() is False

    def test_inactivo_no_se_vende_aunque_tenga_stock(self):
        assert producto(stock=10, activo=False).disponible_para_venta() is False

    def test_eliminado_no_se_vende(self):
        assert producto(stock=10, deleted_at=AHORA).disponible_para_venta() is False

    def test_stock_negativo_no_se_vende(self):
        """No debería pasar (hay CHECK en BD), pero la regla no depende de eso."""
        assert producto(stock=-1).disponible_para_venta() is False


class TestProductoRequiereReposicion:
    def test_stock_por_debajo_del_minimo(self):
        assert producto(stock=2, stock_minimo=5).requiere_reposicion() is True

    def test_stock_igual_al_minimo_ya_alerta(self):
        """El mínimo es el punto de pedido: al tocarlo hay que reponer."""
        assert producto(stock=5, stock_minimo=5).requiere_reposicion() is True

    def test_stock_por_encima_no_alerta(self):
        assert producto(stock=6, stock_minimo=5).requiere_reposicion() is False

    def test_sin_umbral_definido_nunca_alerta(self):
        """`stock_minimo = 0` significa 'sin umbral'. Sin esta regla, todo
        producto agotado sin umbral generaría ruido permanente (HU-B13)."""
        assert producto(stock=0, stock_minimo=0).requiere_reposicion() is False

    def test_producto_inactivo_no_alerta(self):
        p = producto(stock=0, stock_minimo=5, activo=False)
        assert p.requiere_reposicion() is False

    def test_producto_eliminado_no_alerta(self):
        p = producto(stock=0, stock_minimo=5, deleted_at=AHORA)
        assert p.requiere_reposicion() is False


# =============================================================================
# Proveedor
# =============================================================================


class TestProveedorDeuda:
    def test_sin_deuda(self):
        assert proveedor().tiene_deuda() is False

    def test_con_deuda(self):
        assert proveedor(deuda_actual=Decimal("10")).tiene_deuda() is True

    def test_una_compra_a_credito_suma(self):
        p = proveedor(deuda_actual=Decimal("100"))
        p.aplicar_delta_deuda(Decimal("50"))
        assert p.deuda_actual == Decimal("150")

    def test_un_pago_resta(self):
        p = proveedor(deuda_actual=Decimal("100"))
        p.aplicar_delta_deuda(Decimal("-40"))
        assert p.deuda_actual == Decimal("60")

    def test_puede_saldarse_exactamente(self):
        p = proveedor(deuda_actual=Decimal("100"))
        p.aplicar_delta_deuda(Decimal("-100"))
        assert p.deuda_actual == Decimal("0")
        assert p.tiene_deuda() is False

    def test_no_puede_quedar_negativa(self):
        """Pagar más de lo que se debe es un error de carga, no un saldo a favor."""
        p = proveedor(deuda_actual=Decimal("100"))
        with pytest.raises(ValidacionError):
            p.aplicar_delta_deuda(Decimal("-100.01"))

    def test_la_deuda_no_cambia_si_el_delta_es_invalido(self):
        p = proveedor(deuda_actual=Decimal("100"))
        with pytest.raises(ValidacionError):
            p.aplicar_delta_deuda(Decimal("-999"))
        assert p.deuda_actual == Decimal("100")

    def test_usa_decimal_no_float(self):
        """Con float, 0.1+0.2 no da 0.3 y la deuda se desfasa con el tiempo."""
        p = proveedor(deuda_actual=Decimal("0"))
        for _ in range(3):
            p.aplicar_delta_deuda(Decimal("0.1"))
        assert p.deuda_actual == Decimal("0.3")


# =============================================================================
# SolicitudIngreso: transiciones de estado
# =============================================================================


class TestSolicitudTransiciones:
    def test_una_pendiente_se_reconoce_como_tal(self):
        assert solicitud().estado == EstadoSolicitud(EstadoSolicitud.PENDIENTE)

    def test_pendiente_puede_aprobarse_y_rechazarse(self):
        s = solicitud()
        assert s.puede_ser_aprobada() is True
        assert s.puede_ser_rechazada() is True

    def test_aprobar_deja_constancia_de_quien_y_cuando(self):
        s = solicitud()
        s.aprobar(usuario_id=9, nombre="Admin")
        assert s.estado == EstadoSolicitud(EstadoSolicitud.APROBADA)
        assert s.revisado_por == 9
        assert s.revisado_por_nombre == "Admin"
        assert s.revisado_en is not None

    def test_rechazar_exige_motivo(self):
        s = solicitud()
        s.rechazar(usuario_id=9, nombre="Admin", motivo="La boleta no coincide")
        assert s.estado == EstadoSolicitud(EstadoSolicitud.RECHAZADA)
        assert s.motivo_rechazo == "La boleta no coincide"

    @pytest.mark.parametrize("motivo", ["", "   ", "abc", "1234"])
    def test_rechazar_con_motivo_corto_o_vacio_falla(self, motivo):
        """Un motivo de 3 letras no explica nada a quien lo lea después."""
        with pytest.raises(ValidacionError):
            solicitud().rechazar(usuario_id=9, nombre="Admin", motivo=motivo)

    def test_no_se_puede_aprobar_dos_veces(self):
        """Doble aprobación duplicaría el stock ingresado."""
        s = solicitud()
        s.aprobar(usuario_id=9, nombre="Admin")
        with pytest.raises(ConflictoError):
            s.aprobar(usuario_id=9, nombre="Admin")

    def test_no_se_puede_rechazar_una_ya_aprobada(self):
        s = solicitud()
        s.aprobar(usuario_id=9, nombre="Admin")
        with pytest.raises(ConflictoError):
            s.rechazar(usuario_id=9, nombre="Admin", motivo="me arrepentí")

    def test_no_se_puede_aprobar_una_ya_rechazada(self):
        s = solicitud()
        s.rechazar(usuario_id=9, nombre="Admin", motivo="boleta ilegible")
        with pytest.raises(ConflictoError):
            s.aprobar(usuario_id=9, nombre="Admin")

    def test_los_estados_finales_son_terminales(self):
        for accion in ("aprobar", "rechazar"):
            s = solicitud()
            if accion == "aprobar":
                s.aprobar(usuario_id=9, nombre="A")
            else:
                s.rechazar(usuario_id=9, nombre="A", motivo="motivo válido")
            assert s.puede_ser_aprobada() is False
            assert s.puede_ser_rechazada() is False


class TestSolicitudEdicion:
    def test_el_dueno_puede_editar_la_suya(self):
        s = solicitud(solicitado_por=2)
        assert s.puede_ser_editada_por(usuario_id=2, es_admin=False) is True

    def test_otro_cajero_no_puede_editarla(self):
        s = solicitud(solicitado_por=2)
        assert s.puede_ser_editada_por(usuario_id=3, es_admin=False) is False

    def test_el_admin_puede_editar_cualquiera(self):
        s = solicitud(solicitado_por=2)
        assert s.puede_ser_editada_por(usuario_id=99, es_admin=True) is True

    def test_una_solicitud_ya_revisada_no_se_edita(self):
        s = solicitud(solicitado_por=2)
        s.aprobar(usuario_id=9, nombre="Admin")
        assert s.puede_ser_editada_por(usuario_id=2, es_admin=False) is False
        assert s.puede_ser_editada_por(usuario_id=99, es_admin=True) is False


# =============================================================================
# MovimientoInventario: el signo lo dicta el tipo
# =============================================================================


class TestMovimientoInventario:
    def test_ingreso_es_positivo(self):
        m = MovimientoInventario.ingreso(
            producto_id=1, cantidad=10, solicitud_ingreso_id=5,
            usuario_id=1, usuario_nombre="Admin",
        )
        assert m.cantidad == 10
        assert str(m.tipo) == "ingreso"

    def test_venta_es_negativa(self):
        """Se pasa la cantidad vendida en positivo y la entidad la invierte:
        quien llama no tiene que acordarse del signo."""
        m = MovimientoInventario.venta(
            producto_id=1, cantidad=3, usuario_id=1, usuario_nombre="Cajero"
        )
        assert m.cantidad == -3

    def test_devolucion_es_positiva(self):
        m = MovimientoInventario.devolucion(
            producto_id=1, cantidad=2, motivo="cliente devolvió",
            usuario_id=1, usuario_nombre="Cajero",
        )
        assert m.cantidad == 2

    @pytest.mark.parametrize("cantidad", [5, -5])
    def test_el_ajuste_admite_los_dos_signos(self, cantidad):
        """El ajuste manual sirve tanto para faltantes como para sobrantes."""
        m = MovimientoInventario.ajuste(
            producto_id=1, cantidad=cantidad, motivo="conteo físico",
            usuario_id=1, usuario_nombre="Admin",
        )
        assert m.cantidad == cantidad
        assert m.motivo == "conteo físico"

    def test_el_ingreso_queda_vinculado_a_su_solicitud(self):
        m = MovimientoInventario.ingreso(
            producto_id=1, cantidad=10, solicitud_ingreso_id=77,
            usuario_id=1, usuario_nombre="Admin",
        )
        assert m.solicitud_ingreso_id == 77


# =============================================================================
# PagoProveedor
# =============================================================================


class TestPagoProveedor:
    def test_compra_a_credito(self):
        p = PagoProveedor.crear_compra_credito(
            proveedor_id=1, monto=Decimal("500"), concepto="Ingreso #5",
            fecha=AHORA.date(), solicitud_ingreso_id=5,
            usuario_id=1, usuario_nombre="Admin",
        )
        assert str(p.tipo) == "compra_credito"
        assert p.monto == Decimal("500")
        assert p.solicitud_ingreso_id == 5

    def test_pago(self):
        p = PagoProveedor.crear_pago(
            proveedor_id=1, monto=Decimal("200"), concepto="Pago parcial",
            fecha=AHORA.date(), usuario_id=1, usuario_nombre="Admin",
        )
        assert str(p.tipo) == "pago"
        assert p.solicitud_ingreso_id is None, (
            "un pago no cuelga de una solicitud: eso es sólo de las compras"
        )
