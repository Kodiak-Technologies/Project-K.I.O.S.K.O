"""Costo de mercadería por proveedor en el reporte de ventas.

No hay tabla de gastos: el costo y su asociación al proveedor salen de las
solicitudes de ingreso APROBADAS. Por eso el desglose por proveedor tiene que
sumar exactamente lo mismo que `total_egresos`, que se calcula aparte.
"""

from app.modules.modulo_d_documentos.application.generar_reporte_ventas_usecase import (
    GenerarReporteVentasUseCase,
)


class VentaDataFake:
    def __init__(self, ventas=None, detalles=None):
        self._ventas = ventas or []
        self._detalles = detalles or {}

    async def listar_ventas(self, desde, hasta):
        return self._ventas

    async def obtener_detalle_venta(self, venta_id):
        return self._detalles.get(venta_id, [])


class EgresosDataFake:
    """Devuelve lo que devolvería el SQL: 'Sin proveedor' ya resuelto."""

    def __init__(self, por_proveedor):
        self._por_proveedor = por_proveedor

    async def total_egresos(self, desde, hasta):
        return sum(p["monto"] for p in self._por_proveedor)

    async def costo_por_proveedor(self, desde, hasta):
        return list(self._por_proveedor)


RANGO = ("2026-07-01", "2026-07-31")


class TestCostoPorProveedor:
    async def test_desglosa_el_gasto_por_proveedor(self):
        egresos = EgresosDataFake(
            [
                {"proveedor": "Distribuidora Lima", "monto": 800.0, "unidades": 120, "ingresos": 3},
                {"proveedor": "Abarrotes del Sur", "monto": 450.0, "unidades": 60, "ingresos": 2},
            ]
        )
        caso = GenerarReporteVentasUseCase(VentaDataFake(), egresos)
        resumen = await caso.ejecutar(*RANGO)

        assert [c.proveedor for c in resumen.costo_por_proveedor] == [
            "Distribuidora Lima",
            "Abarrotes del Sur",
        ]
        assert resumen.costo_por_proveedor[0].monto == 800.0
        assert resumen.costo_por_proveedor[0].unidades == 120
        assert resumen.costo_por_proveedor[0].ingresos == 3

    async def test_las_solicitudes_sin_proveedor_aparecen_como_sin_proveedor(self):
        """Descartarlas dejaría el desglose sin cuadrar contra el total."""
        egresos = EgresosDataFake(
            [
                {"proveedor": "Distribuidora Lima", "monto": 800.0, "unidades": 120, "ingresos": 3},
                {"proveedor": "Sin proveedor", "monto": 200.0, "unidades": 25, "ingresos": 1},
            ]
        )
        caso = GenerarReporteVentasUseCase(VentaDataFake(), egresos)
        resumen = await caso.ejecutar(*RANGO)

        assert "Sin proveedor" in [c.proveedor for c in resumen.costo_por_proveedor]

    async def test_el_desglose_suma_igual_que_el_total_de_egresos(self):
        egresos = EgresosDataFake(
            [
                {"proveedor": "Distribuidora Lima", "monto": 800.0, "unidades": 120, "ingresos": 3},
                {"proveedor": "Sin proveedor", "monto": 200.5, "unidades": 25, "ingresos": 1},
            ]
        )
        caso = GenerarReporteVentasUseCase(VentaDataFake(), egresos)
        resumen = await caso.ejecutar(*RANGO)

        assert sum(c.monto for c in resumen.costo_por_proveedor) == resumen.total_egresos

    async def test_sin_ingresos_aprobados_la_tabla_queda_vacia(self):
        caso = GenerarReporteVentasUseCase(VentaDataFake(), EgresosDataFake([]))
        resumen = await caso.ejecutar(*RANGO)

        assert resumen.costo_por_proveedor == []
        assert resumen.total_egresos == 0.0

    async def test_sin_proveedor_de_egresos_no_rompe_el_reporte(self):
        """El use case acepta no tener el provider (tests y arranque parcial)."""
        caso = GenerarReporteVentasUseCase(VentaDataFake())
        resumen = await caso.ejecutar(*RANGO)

        assert resumen.costo_por_proveedor == []
