"""Resto del catálogo: edición, baja, categorías y la lista de reposición.

La baja de producto es lógica a propósito: el histórico de ventas y movimientos
apunta al producto, y las FKs son `ON DELETE RESTRICT`. Borrarlo de verdad
rompería la contabilidad.
"""

import pytest

from app.modules.modulo_b_inventario.application.crear_categoria_usecase import (
    CrearCategoriaUseCase,
)
from app.modules.modulo_b_inventario.application.editar_producto_usecase import (
    EditarProductoUseCase,
)
from app.modules.modulo_b_inventario.application.eliminar_producto_usecase import (
    EliminarProductoUseCase,
)
from app.modules.modulo_b_inventario.application.listar_productos_por_reponer_usecase import (
    ListarProductosPorReponerUseCase,
)
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError

from .dobles import (
    AuditoriaFake,
    CategoriaRepoFake,
    ProductoRepoFake,
    producto,
)

CTX = dict(usuario_id=1, usuario_nombre="Admin", ip="", user_agent="")


class TestEliminarProducto:
    def _caso(self, productos):
        repo = ProductoRepoFake(productos)
        aud = AuditoriaFake()
        return EliminarProductoUseCase(repo, aud), repo, aud

    async def test_es_baja_logica(self):
        """El histórico de ventas apunta al producto: no se puede borrar."""
        p = producto(id=1)
        caso, _, _ = self._caso([p])
        await caso.ejecutar(producto_id=1, **CTX)
        assert p.deleted_at is not None
        assert p.deleted_by == 1

    async def test_lo_saca_del_punto_de_venta(self):
        p = producto(id=1, activo=True, stock=10)
        caso, _, _ = self._caso([p])
        await caso.ejecutar(producto_id=1, **CTX)
        assert p.activo is False
        assert p.disponible_para_venta() is False

    async def test_la_fila_sigue_existiendo(self):
        caso, repo, _ = self._caso([producto(id=1)])
        await caso.ejecutar(producto_id=1, **CTX)
        assert len(repo.productos) == 1

    async def test_producto_inexistente(self):
        caso, _, _ = self._caso([])
        with pytest.raises(NoEncontradoError):
            await caso.ejecutar(producto_id=404, **CTX)

    async def test_no_se_puede_eliminar_dos_veces(self):
        from datetime import datetime, timezone

        caso, _, _ = self._caso(
            [producto(id=1, deleted_at=datetime.now(timezone.utc))]
        )
        with pytest.raises(NoEncontradoError):
            await caso.ejecutar(producto_id=1, **CTX)

    async def test_queda_registrado_en_bitacora(self):
        caso, _, aud = self._caso([producto(id=1)])
        await caso.ejecutar(producto_id=1, motivo="descontinuado", **CTX)
        assert aud.eventos


class TestEditarProducto:
    def _caso(self, productos):
        repo = ProductoRepoFake(productos)
        aud = AuditoriaFake()
        return EditarProductoUseCase(repo, aud), repo, aud

    async def test_aplica_los_cambios(self):
        p = producto(id=1, nombre="Viejo")
        caso, _, _ = self._caso([p])
        await caso.ejecutar(producto_id=1, cambios={"nombre": "Nuevo"}, **CTX)
        assert p.nombre == "Nuevo"

    @pytest.mark.parametrize("campo", ["precio", "precio_compra_actual"])
    async def test_los_precios_no_se_editan_por_aca(self, campo):
        """Van por `PATCH /precio`, que además deja fila en el historial. Si se
        aceptaran acá, el precio cambiaría sin rastro."""
        caso, _, _ = self._caso([producto(id=1)])
        with pytest.raises(ValidacionError):
            await caso.ejecutar(producto_id=1, cambios={campo: 99}, **CTX)

    async def test_el_precio_no_cambia_al_rechazarlo(self):
        from decimal import Decimal

        p = producto(id=1, precio=Decimal("3.50"))
        caso, _, _ = self._caso([p])
        with pytest.raises(ValidacionError):
            await caso.ejecutar(producto_id=1, cambios={"precio": 99}, **CTX)
        assert p.precio == Decimal("3.50")

    async def test_permite_desasignar_la_categoria(self):
        """`categoria_id=None` explícito significa 'sacale la categoría'."""
        p = producto(id=1, categoria_id=3)
        caso, _, _ = self._caso([p])
        await caso.ejecutar(producto_id=1, cambios={"categoria_id": None}, **CTX)
        assert p.categoria_id is None


class TestCrearCategoria:
    def _caso(self, existentes=None):
        repo = CategoriaRepoFake(existentes or [])
        aud = AuditoriaFake()
        return CrearCategoriaUseCase(repo, aud), repo, aud

    async def test_crea_con_nombre_y_descripcion(self):
        caso, _, _ = self._caso()
        c = await caso.ejecutar(
            nombre="Galletas", descripcion="Dulces y saladas", **CTX
        )
        assert c.id is not None
        assert c.nombre == "Galletas"
        assert c.descripcion == "Dulces y saladas"

    async def test_la_descripcion_es_opcional(self):
        caso, _, _ = self._caso()
        c = await caso.ejecutar(nombre="Bebidas", descripcion=None, **CTX)
        assert c.descripcion is None

    async def test_guarda_quien_la_creo(self):
        """Se persiste en el mismo INSERT: antes hacía un UPDATE extra."""
        caso, _, _ = self._caso()
        c = await caso.ejecutar(nombre="Bebidas", descripcion=None, **CTX)
        assert c.creado_por == 1
        assert c.creado_por_nombre == "Admin"

    async def test_queda_registrado_en_bitacora(self):
        caso, _, aud = self._caso()
        await caso.ejecutar(nombre="Bebidas", descripcion=None, **CTX)
        assert aud.eventos


class TestListarPorReponer:
    def _caso(self, productos):
        repo = ProductoRepoFake(productos)
        return ListarProductosPorReponerUseCase(repo), repo

    async def test_trae_los_que_estan_en_o_bajo_el_minimo(self):
        caso, _ = self._caso(
            [
                producto(id=1, stock=2, stock_minimo=5),  # bajo
                producto(id=2, stock=5, stock_minimo=5),  # en el mínimo
                producto(id=3, stock=9, stock_minimo=5),  # ok
            ]
        )
        items, *_ = await caso.ejecutar()
        assert sorted(i.producto.id for i in items) == [1, 2]

    async def test_ignora_los_que_no_tienen_umbral(self):
        """`stock_minimo = 0` es 'sin umbral': si no, todo agotado haría ruido."""
        caso, _ = self._caso([producto(id=1, stock=0, stock_minimo=0)])
        items, *_ = await caso.ejecutar()
        assert items == []

    async def test_puede_filtrar_los_ya_avisados(self):
        caso, _ = self._caso(
            [
                producto(id=1, stock=1, stock_minimo=5, alerta_stock_notificada=True),
                producto(id=2, stock=1, stock_minimo=5, alerta_stock_notificada=False),
            ]
        )
        items, *_ = await caso.ejecutar(solo_no_notificadas=True)
        assert [i.producto.id for i in items] == [2]

    async def test_calcula_cuanto_falta(self):
        caso, _ = self._caso([producto(id=1, stock=2, stock_minimo=5)])
        items, *_ = await caso.ejecutar()
        assert items[0].faltante == 3

    @pytest.mark.parametrize("page,page_size", [(0, 20), (1, 0), (1, 101)])
    async def test_valida_la_paginacion(self, page, page_size):
        caso, _ = self._caso([])
        with pytest.raises(ValidacionError):
            await caso.ejecutar(page=page, page_size=page_size)
