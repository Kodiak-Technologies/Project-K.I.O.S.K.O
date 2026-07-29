"""Registro y rechazo de solicitudes de ingreso (los otros dos pasos del flujo).

El ingreso es de dos pasos a propósito: el cajero registra lo que llegó con la
foto de la boleta, y recién la administradora lo aprueba. Registrar **no toca el
stock** — eso pasa sólo al aprobar.
"""

from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.rechazar_ingreso_usecase import (
    RechazarIngresoUseCase,
)
from app.modules.modulo_b_inventario.application.registrar_ingreso_usecase import (
    LineaSolicitudDTO,
    RegistrarIngresoUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import SolicitudIngreso
from app.modules.modulo_b_inventario.domain.value_objects import EstadoSolicitud
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    DetalleRepoFake,
    NotificadorFake,
    ProductoRepoFake,
    ProveedorRepoFake,
    SolicitudRepoFake,
    producto,
    proveedor,
)

CTX = dict(usuario_id=2, usuario_nombre="Cajero", ip="", user_agent="")
FOTO = "https://drive.google.com/uc?export=view&id=abc"


def linea(producto_id=1, cantidad=10, total="20.00", **kwargs) -> LineaSolicitudDTO:
    """`total` es el monto de la línea en la boleta, no el unitario."""
    return LineaSolicitudDTO(
        producto_id=producto_id,
        cantidad=cantidad,
        precio_compra_total=Decimal(total),
        **kwargs,
    )


def linea_nueva(codigo="7501234567890", nombre="Esponja verde", **kwargs):
    """Línea que propone un producto que todavía no está en el catálogo."""
    return LineaSolicitudDTO(
        producto_id=None,
        cantidad=kwargs.pop("cantidad", 7),
        precio_compra_total=Decimal(kwargs.pop("total", "20.00")),
        nuevo_codigo=codigo,
        nuevo_nombre=nombre,
        **kwargs,
    )


class EscenarioRegistro:
    def __init__(self, productos=None, proveedores=None):
        self.solicitudes = SolicitudRepoFake()
        self.detalles = DetalleRepoFake()
        self.productos = ProductoRepoFake(
            productos if productos is not None else [producto(id=1)]
        )
        self.proveedores = ProveedorRepoFake(
            proveedores if proveedores is not None else [proveedor(id=7)]
        )
        self.auditoria = AuditoriaFake()
        self.notificador = NotificadorFake()
        self.caso = RegistrarIngresoUseCase(
            self.solicitudes,
            self.detalles,
            self.productos,
            self.proveedores,
            self.auditoria,
            self.notificador,
        )

    async def registrar(self, **kwargs):
        datos = dict(
            proveedor_id=7, foto_boleta_url=FOTO, lineas=[linea()], **CTX
        )
        datos.update(kwargs)
        return await self.caso.ejecutar(**datos)


class TestRegistrarIngreso:
    async def test_nace_pendiente_de_revision(self):
        e = EscenarioRegistro()
        s = await e.registrar()
        assert s.estado == EstadoSolicitud(EstadoSolicitud.PENDIENTE)

    async def test_NO_toca_el_stock(self):
        """El stock sube recién al aprobar: ese es el punto del flujo de 2 pasos."""
        p = producto(id=1, stock=10)
        e = EscenarioRegistro(productos=[p])
        await e.registrar(lineas=[linea(producto_id=1, cantidad=50)])
        assert p.stock == 10

    async def test_guarda_quien_la_registro(self):
        e = EscenarioRegistro()
        s = await e.registrar()
        assert s.solicitado_por == 2
        assert s.solicitado_por_nombre == "Cajero"

    async def test_guarda_las_lineas(self):
        e = EscenarioRegistro(productos=[producto(id=1), producto(id=2)])
        await e.registrar(lineas=[linea(producto_id=1), linea(producto_id=2)])
        assert len(e.detalles.creados) == 2

    async def test_el_proveedor_es_opcional(self):
        """Una compra de contado en el mercado puede no tener proveedor cargado."""
        e = EscenarioRegistro()
        s = await e.registrar(proveedor_id=None)
        assert s.proveedor_id is None

    async def test_avisa_a_la_administradora(self):
        e = EscenarioRegistro()
        await e.registrar()
        assert "SOLICITUD_INGRESO" in e.notificador.tipos()

    async def test_funciona_sin_notificador(self):
        """Un aviso caído no puede impedir registrar la mercadería."""
        caso = RegistrarIngresoUseCase(
            SolicitudRepoFake(),
            DetalleRepoFake(),
            ProductoRepoFake([producto(id=1)]),
            ProveedorRepoFake([proveedor(id=7)]),
            AuditoriaFake(),
            None,
        )
        s = await caso.ejecutar(
            proveedor_id=7, foto_boleta_url=FOTO, lineas=[linea()], **CTX
        )
        assert s.id is not None

    @pytest.mark.parametrize("foto", ["", "   "])
    async def test_la_foto_de_la_boleta_es_opcional(self, foto):
        """No toda compra viene con boleta; exigirla dejaba mercadería sin registrar."""
        e = EscenarioRegistro()
        s = await e.registrar(foto_boleta_url=foto)
        assert s.id is not None
        assert s.foto_boleta_url == ""

    async def test_se_puede_registrar_sin_pasar_la_foto(self):
        """El parámetro tiene default: el cliente puede omitirlo del todo."""
        e = EscenarioRegistro()
        s = await e.caso.ejecutar(proveedor_id=7, lineas=[linea()], **CTX)
        assert s.foto_boleta_url == ""


class TestRegistroRechazado:
    async def test_sin_lineas(self):
        e = EscenarioRegistro()
        with pytest.raises(ValidacionError):
            await e.registrar(lineas=[])

    @pytest.mark.parametrize("cantidad", [0, -1])
    async def test_cantidad_invalida(self, cantidad):
        e = EscenarioRegistro()
        with pytest.raises(ValidacionError):
            await e.registrar(lineas=[linea(cantidad=cantidad)])

    async def test_precio_negativo(self):
        e = EscenarioRegistro()
        with pytest.raises(ValidacionError):
            await e.registrar(lineas=[linea(total="-1")])

    async def test_el_error_dice_QUE_linea_falla(self):
        """Con 20 líneas cargadas, 'cantidad inválida' a secas no sirve."""
        e = EscenarioRegistro(productos=[producto(id=1), producto(id=2)])
        with pytest.raises(ValidacionError) as err:
            await e.registrar(
                lineas=[linea(producto_id=1), linea(producto_id=2, cantidad=0)]
            )
        assert "2" in str(err.value)

    async def test_producto_inexistente(self):
        e = EscenarioRegistro(productos=[])
        with pytest.raises(NoEncontradoError):
            await e.registrar(lineas=[linea(producto_id=404)])

    async def test_producto_borrado(self):
        from datetime import datetime, timezone

        e = EscenarioRegistro(
            productos=[producto(id=1, deleted_at=datetime.now(timezone.utc))]
        )
        with pytest.raises(NoEncontradoError):
            await e.registrar()

    async def test_proveedor_inexistente(self):
        e = EscenarioRegistro(proveedores=[])
        with pytest.raises(NoEncontradoError):
            await e.registrar(proveedor_id=404)

    async def test_no_crea_la_solicitud_si_algo_falla(self):
        e = EscenarioRegistro()
        with pytest.raises(ValidacionError):
            await e.registrar(lineas=[])
        assert e.solicitudes.solicitudes == []


class TestRechazarIngreso:
    def _caso(self, sol=None):
        s = sol if sol is not None else SolicitudIngreso(
            id=1,
            estado=EstadoSolicitud(EstadoSolicitud.PENDIENTE),
            proveedor_id=7,
            foto_boleta_url=FOTO,
            solicitado_por=2,
            solicitado_por_nombre="Cajero",
        )
        repo = SolicitudRepoFake([s] if s else [])
        aud = AuditoriaFake()
        return RechazarIngresoUseCase(repo, aud), s, aud

    async def test_rechaza_con_motivo(self):
        caso, s, _ = self._caso()
        r = await caso.ejecutar(
            solicitud_id=1, motivo="La boleta no coincide con lo recibido",
            usuario_id=9, usuario_nombre="Admin",
        )
        assert r.estado == EstadoSolicitud(EstadoSolicitud.RECHAZADA)
        assert r.motivo_rechazo == "La boleta no coincide con lo recibido"

    @pytest.mark.parametrize("motivo", ["", "   ", "abcd"])
    async def test_el_motivo_debe_ser_explicativo(self, motivo):
        caso, _, _ = self._caso()
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                solicitud_id=1, motivo=motivo, usuario_id=9, usuario_nombre="Admin"
            )

    async def test_el_motivo_se_recorta(self):
        caso, _, _ = self._caso()
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                solicitud_id=1, motivo="  ab  ", usuario_id=9, usuario_nombre="Admin"
            )

    async def test_solicitud_inexistente(self):
        caso, _, _ = self._caso(sol=None)
        with pytest.raises(NoEncontradoError):
            await caso.ejecutar(
                solicitud_id=404, motivo="motivo suficiente",
                usuario_id=9, usuario_nombre="Admin",
            )

    async def test_no_se_puede_rechazar_dos_veces(self):
        caso, _, _ = self._caso()
        await caso.ejecutar(
            solicitud_id=1, motivo="motivo suficiente",
            usuario_id=9, usuario_nombre="Admin",
        )
        with pytest.raises(ConflictoError) as err:
            await caso.ejecutar(
                solicitud_id=1, motivo="otro motivo suficiente",
                usuario_id=9, usuario_nombre="Admin",
            )
        assert getattr(err.value, "code", None) == "ALREADY_REJECTED"

    async def test_una_aprobada_no_se_puede_rechazar(self):
        s = SolicitudIngreso(
            id=1,
            estado=EstadoSolicitud(EstadoSolicitud.PENDIENTE),
            proveedor_id=7,
            foto_boleta_url=FOTO,
            solicitado_por=2,
            solicitado_por_nombre="Cajero",
        )
        s.aprobar(usuario_id=9, nombre="Admin")
        caso, _, _ = self._caso(sol=s)
        with pytest.raises(ConflictoError):
            await caso.ejecutar(
                solicitud_id=1, motivo="me arrepentí de aprobarla",
                usuario_id=9, usuario_nombre="Admin",
            )

    async def test_el_motivo_queda_en_bitacora(self):
        caso, _, aud = self._caso()
        await caso.ejecutar(
            solicitud_id=1, motivo="faltaban 3 cajas",
            usuario_id=9, usuario_nombre="Admin",
        )
        assert aud.eventos[0]["motivo"] == "faltaban 3 cajas"
