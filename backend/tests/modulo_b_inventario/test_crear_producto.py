"""`CrearProductoUseCase`: alta en el catálogo.

Lo más particular del alta es el **código**: puede venir de un código de barras
real escaneado, o generarse interno con formato `PAP-NNN`. Los dos caminos no
pueden mezclarse — si alguien manda a mano algo con pinta de código interno, se
rechaza, porque después colisionaría con los autogenerados.
"""

from decimal import Decimal

import pytest

from app.modules.modulo_b_inventario.application.crear_producto_usecase import (
    CrearProductoUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Categoria
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    CategoriaRepoFake,
    HistorialPrecioRepoFake,
    ProductoRepoFake,
    producto,
)

CTX = dict(usuario_id=1, usuario_nombre="Admin", ip="", user_agent="")


def categoria(id=1, nombre="Galletas") -> Categoria:
    return Categoria(id=id, nombre=nombre)


class Escenario:
    def __init__(self, productos=None, categorias=None):
        self.productos = ProductoRepoFake(productos or [])
        self.categorias = CategoriaRepoFake(
            categorias if categorias is not None else [categoria()]
        )
        self.historial = HistorialPrecioRepoFake()
        self.auditoria = AuditoriaFake()
        self.caso = CrearProductoUseCase(
            self.productos, self.categorias, self.historial, self.auditoria
        )

    async def crear(self, **kwargs):
        datos = dict(
            codigo="7750000000014",
            nombre="Galleta Soda",
            categoria_id=1,
            precio_venta=Decimal("3.50"),
            precio_compra_actual=Decimal("2.60"),
            **CTX,
        )
        datos.update(kwargs)
        return await self.caso.ejecutar(**datos)


class TestAltaConCodigoDeBarras:
    async def test_crea_el_producto(self):
        e = Escenario()
        p = await e.crear()
        assert p.id is not None
        assert p.codigo == "7750000000014"
        assert p.nombre == "Galleta Soda"

    async def test_recorta_espacios_del_nombre_y_del_codigo(self):
        e = Escenario()
        p = await e.crear(nombre="  Galleta  ", codigo="  775000  ")
        assert p.nombre == "Galleta"
        assert p.codigo == "775000"

    async def test_puede_nacer_con_stock_inicial(self):
        e = Escenario()
        p = await e.crear(stock_inicial=25, stock_minimo=5)
        assert p.stock == 25 and p.stock_minimo == 5

    async def test_sin_stock_inicial_arranca_en_cero(self):
        e = Escenario()
        p = await e.crear()
        assert p.stock == 0

    async def test_la_categoria_es_opcional(self):
        e = Escenario()
        p = await e.crear(categoria_id=None)
        assert p.categoria_id is None

    async def test_queda_registrado_en_bitacora(self):
        e = Escenario()
        await e.crear()
        assert e.auditoria.eventos


class TestValidaciones:
    @pytest.mark.parametrize("nombre", ["", "   "])
    async def test_nombre_obligatorio(self, nombre):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.crear(nombre=nombre)

    @pytest.mark.parametrize("precio", [Decimal("0"), Decimal("-1")])
    async def test_precio_de_venta_debe_ser_positivo(self, precio):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.crear(precio_venta=precio)

    async def test_precio_de_compra_no_puede_ser_negativo(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.crear(precio_compra_actual=Decimal("-1"))

    async def test_precio_de_compra_cero_si_se_permite(self):
        """Un obsequio del proveedor entra con costo 0."""
        e = Escenario()
        p = await e.crear(precio_compra_actual=Decimal("0"))
        assert p.precio_compra_actual == Decimal("0")

    @pytest.mark.parametrize("campo", ["stock_inicial", "stock_minimo"])
    async def test_stock_negativo(self, campo):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.crear(**{campo: -1})

    @pytest.mark.parametrize("codigo", [None, "", "   "])
    async def test_codigo_obligatorio_si_no_es_interno(self, codigo):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.crear(codigo=codigo, es_codigo_interno=False)

    async def test_categoria_inexistente(self):
        e = Escenario(categorias=[])
        with pytest.raises(NoEncontradoError):
            await e.crear(categoria_id=99)

    async def test_no_crea_nada_si_una_validacion_falla(self):
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.crear(precio_venta=Decimal("0"))
        assert e.productos.productos == []


class TestUnicidadDelCodigo:
    async def test_codigo_repetido(self):
        e = Escenario([producto(id=1, codigo="775000")])
        with pytest.raises(ConflictoError):
            await e.crear(codigo="775000")

    async def test_el_codigo_de_un_producto_borrado_tambien_choca(self):
        """El caso de uso avisa con un mensaje claro en vez de dejar que
        reviente el UNIQUE de la BD."""
        from datetime import datetime, timezone

        borrado = producto(id=1, codigo="775000", deleted_at=datetime.now(timezone.utc))
        e = Escenario([borrado])
        with pytest.raises(ConflictoError):
            await e.crear(codigo="775000")


class TestCodigoInterno:
    async def test_lo_genera_solo(self):
        e = Escenario()
        p = await e.crear(codigo=None, es_codigo_interno=True)
        assert p.codigo.startswith("PAP-")
        assert p.es_codigo_interno is True

    async def test_es_correlativo(self):
        """No puede ser aleatorio ni basado en la hora: dos altas en el mismo
        segundo se pisarían."""
        e = Escenario()
        codigos = [
            (await e.crear(codigo=None, nombre=f"P{i}", es_codigo_interno=True)).codigo
            for i in range(3)
        ]
        assert codigos == ["PAP-001", "PAP-002", "PAP-003"]

    async def test_ignora_el_codigo_que_le_manden(self):
        e = Escenario()
        p = await e.crear(codigo="LO-QUE-SEA", es_codigo_interno=True)
        assert p.codigo.startswith("PAP-")

    async def test_rechaza_un_codigo_manual_con_formato_interno(self):
        """Si se aceptara, colisionaría con un autogenerado más adelante."""
        e = Escenario()
        with pytest.raises(ValidacionError):
            await e.crear(codigo="PAP-001", es_codigo_interno=False)

    async def test_un_codigo_manual_con_otro_prefijo_si_se_acepta(self):
        """Sólo molesta el prefijo real del sistema; `BC-12345` es un código
        de barras válido de un proveedor."""
        e = Escenario()
        p = await e.crear(codigo="BC-12345", es_codigo_interno=False)
        assert p.codigo == "BC-12345"
