"""`AprobarIngresoUseCase`: el momento en que la mercadería entra al inventario.

Es el caso de uso más delicado del módulo porque toca tres cosas a la vez y
todas tienen que quedar consistentes:
  1. sube el stock de cada producto y deja su asiento;
  2. el precio de COMPRA de la boleta pasa a ser el precio de compra vigente
     del producto (el de VENTA no se toca nunca);
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


def linea(producto_id=1, cantidad=10, total="20.00", **kwargs) -> DetalleSolicitud:
    """`total` es el monto de la línea en la boleta, no el precio unitario."""
    return DetalleSolicitud(
        id=kwargs.pop("id", 100),
        solicitud_id=1,
        producto_id=producto_id,
        cantidad=cantidad,
        precio_compra_total=Decimal(total),
        **kwargs,
    )


def linea_nueva(codigo="7501234567890", nombre="Esponja verde", **kwargs):
    """Línea que propone dar de alta un producto al aprobar."""
    return DetalleSolicitud(
        id=kwargs.pop("id", 200),
        solicitud_id=1,
        producto_id=None,
        cantidad=kwargs.pop("cantidad", 7),
        precio_compra_total=Decimal(kwargs.pop("total", "20.00")),
        nuevo_codigo=codigo,
        nuevo_nombre=nombre,
        **kwargs,
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
                linea(producto_id=1, cantidad=10, total="25.00", id=101),
                linea(producto_id=2, cantidad=4, total="12.00", id=102),
            ],
            productos=[producto(id=1, stock=0), producto(id=2, stock=0)],
        )
        r = await e.aprobar()
        assert r.monto_total == Decimal("37.00")  # 25 + 12

    async def test_el_monto_total_es_la_suma_de_la_boleta_sin_reconstruir(self):
        """La regresión que motivó el cambio a total de línea.

        7 unidades por S/ 20 dan un unitario de 2.857…; si el monto se
        reconstruyera como cantidad × unitario redondeado daría 20.02 y la
        deuda al proveedor no cuadraría contra la boleta.
        """
        e = Escenario(
            lineas=[linea(producto_id=1, cantidad=7, total="20.00")],
            productos=[producto(id=1, stock=0)],
        )
        r = await e.aprobar()
        assert r.monto_total == Decimal("20.00")

    async def test_el_precio_de_compra_de_la_boleta_llega_al_producto(self):
        """Antes moría en el detalle y el catálogo quedaba con el precio viejo."""
        p = producto(id=1, stock=0, precio_compra_actual=Decimal("1.00"))
        e = Escenario(
            lineas=[linea(producto_id=1, cantidad=10, total="27.50")], productos=[p]
        )
        await e.aprobar()
        # El catálogo guarda el UNITARIO derivado del total: 27.50 / 10.
        assert p.precio_compra_actual == Decimal("2.75")

    async def test_no_toca_el_precio_de_venta_del_producto(self):
        """La regresión que motivó quitar el margen.

        Aprobar un ingreso recalculaba el precio de venta a partir del costo y
        un margen, así que cada compra le movía el precio al catálogo —y al
        punto de venta— por la espalda. El precio de venta es del catálogo.
        """
        p = producto(id=1, stock=0, precio=Decimal("9.90"))
        e = Escenario(
            lineas=[linea(producto_id=1, cantidad=7, total="20.00")], productos=[p]
        )
        await e.aprobar()
        assert p.precio == Decimal("9.90")

    async def test_no_le_pone_precio_cero_a_un_producto_que_ya_existe(self):
        """El 0 es solo para el producto que nace en esta aprobación."""
        p = producto(id=1, stock=0, precio=Decimal("15.00"))
        e = Escenario(lineas=[linea(producto_id=1)], productos=[p])
        await e.aprobar()
        assert p.precio == Decimal("15.00")

    async def test_no_deja_historial_de_precio_de_venta(self):
        """Ni siquiera un asiento: el precio de venta no participa del ingreso."""
        p = producto(id=1, stock=0, precio=Decimal("9.90"))
        e = Escenario(
            lineas=[linea(producto_id=1, cantidad=7, total="20.00")], productos=[p]
        )
        await e.aprobar()
        assert [h.tipo_precio.valor for h in e.productos.historial] == ["compra"]

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


class TestAltaDeProductoNuevo:
    """El cajero transcribe la boleta aunque el producto no exista todavía.

    El alta ocurre al aprobar y no al registrar: crear productos exige
    `productos.crear`, permiso que el cajero no tiene.
    """

    async def test_crea_el_producto_propuesto(self):
        e = Escenario(lineas=[linea_nueva()], productos=[])
        r = await e.aprobar()
        assert r.productos_creados == 1
        creado = e.productos.productos[0]
        assert creado.codigo == "7501234567890"
        assert creado.nombre == "Esponja verde"

    async def test_nace_sin_precio_de_venta(self):
        """El ingreso no decide a cuánto se vende.

        Antes el precio salía de un margen sobre el costo (20% por defecto), y
        eso hacía que una compra fijara el precio del catálogo —y del punto de
        venta— sin que nadie lo decidiera. Ahora nace en 0 y se le pone precio
        desde el catálogo.
        """
        e = Escenario(lineas=[linea_nueva(cantidad=7, total="20.00")], productos=[])
        await e.aprobar()
        assert e.productos.productos[0].precio == Decimal("0")

    async def test_el_precio_de_venta_no_depende_del_costo(self):
        """Costos muy distintos dan el mismo precio de venta: cero."""
        for total in ("1.00", "999.99"):
            e = Escenario(lineas=[linea_nueva(cantidad=3, total=total)], productos=[])
            await e.aprobar()
            assert e.productos.productos[0].precio == Decimal("0")

    async def test_el_costo_del_catalogo_es_el_unitario_derivado(self):
        e = Escenario(lineas=[linea_nueva(cantidad=7, total="20.00")], productos=[])
        await e.aprobar()
        assert e.productos.productos[0].precio_compra_actual == Decimal("2.86")

    async def test_nace_con_el_stock_de_la_boleta(self):
        """Nace en 0 y el movimiento de ingreso le suma, igual que a cualquiera."""
        e = Escenario(lineas=[linea_nueva(cantidad=7)], productos=[])
        await e.aprobar()
        assert e.productos.productos[0].stock == 7

    async def test_la_linea_queda_atada_al_producto_creado(self):
        e = Escenario(lineas=[linea_nueva()], productos=[])
        await e.aprobar()
        creado = e.productos.productos[0]
        assert e.detalles.por_solicitud[1][0].producto_id == creado.id

    async def test_deja_el_movimiento_de_ingreso(self):
        e = Escenario(lineas=[linea_nueva(cantidad=7)], productos=[])
        await e.aprobar()
        assert len(e.movimientos.movimientos) == 1

    async def test_si_el_codigo_ya_existe_no_se_duplica(self):
        """Alguien pudo crearlo entre el registro y la aprobación."""
        ya_esta = producto(id=1, codigo="7501234567890", stock=0)
        e = Escenario(lineas=[linea_nueva(codigo="7501234567890")], productos=[ya_esta])
        with pytest.raises(ConflictoError):
            await e.aprobar()
        assert len(e.productos.productos) == 1

    async def test_una_solicitud_puede_mezclar_existentes_y_nuevos(self):
        e = Escenario(
            lineas=[linea(producto_id=1, cantidad=2, total="10.00"), linea_nueva()],
            productos=[producto(id=1, stock=0)],
        )
        r = await e.aprobar()
        assert r.productos_creados == 1
        assert r.productos_actualizados == 2


class TestCompraACredito:
    async def test_no_registra_credito_si_no_se_pide(self):
        e = Escenario()
        r = await e.aprobar(registrar_credito=False)
        assert r.credito_registrado is False
        assert e.credito.llamadas == []

    async def test_registra_la_deuda_por_el_monto_total(self):
        e = Escenario(lineas=[linea(cantidad=10, total="20.00")])
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
