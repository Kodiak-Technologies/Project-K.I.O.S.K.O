# Reglas de precio para el ingreso de mercadería (HU-B05/B07).
#
# Por qué existe este módulo: la boleta trae el TOTAL de la línea ("7 esponjas
# — S/ 20"), no el unitario. Derivar uno del otro parece trivial pero tiene dos
# trampas que conviene resolver en un solo lugar y testear:
#
#   1. La división casi nunca da exacta (20/7 = 2.857142…). Si guardáramos el
#      unitario redondeado a 2 decimales y reconstruyéramos el total como
#      cantidad × unitario, daría 20.02: la deuda al proveedor dejaría de
#      cuadrar contra la boleta. Por eso el total es la fuente de verdad y el
#      unitario es SIEMPRE derivado, nunca al revés.
#   2. El precio de venta se redondea hacia arriba al múltiplo de 0.10, no al
#      céntimo: son precios de mostrador y el vuelto se da en monedas.
from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

#: Granularidad del precio de venta de cara al público (S/ 0.10).
PASO_PRECIO_VENTA = Decimal("0.10")

#: Precisión de los montos de dinero persistidos (NUMERIC(10,2)).
CENTIMO = Decimal("0.01")


def costo_unitario(precio_compra_total: Decimal, cantidad: int) -> Decimal:
    """Costo por unidad derivado del total de la línea.

    Se devuelve redondeado al céntimo porque es lo que entra en
    `productos.precio_compra_actual`, que es NUMERIC(10,2). El total original
    queda intacto en la solicitud: este valor es informativo para el catálogo,
    no la base de ningún cálculo de deuda.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser > 0 para derivar el costo unitario.")
    return (Decimal(precio_compra_total) / Decimal(cantidad)).quantize(
        CENTIMO, rounding=ROUND_HALF_UP
    )


def precio_venta_sugerido(
    precio_compra_total: Decimal, cantidad: int, margen_porcentaje: Decimal
) -> Decimal:
    """Precio de venta unitario aplicando el margen y redondeando comercialmente.

    Ejemplo: 7 esponjas a S/ 20 con 20% de margen
        unitario exacto = 2.857142…
        con margen       = 3.428571…
        redondeado ↑ 0.10 = 3.50

    El margen se aplica sobre el unitario EXACTO (sin redondear antes) para no
    arrastrar el error de redondeo al precio final.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser > 0 para calcular el precio de venta.")
    unitario_exacto = Decimal(precio_compra_total) / Decimal(cantidad)
    con_margen = unitario_exacto * (Decimal(1) + Decimal(margen_porcentaje) / Decimal(100))
    # Redondeo comercial: hacia arriba al siguiente múltiplo de 0.10. Nunca
    # queda por debajo del margen pedido.
    pasos = (con_margen / PASO_PRECIO_VENTA).quantize(
        Decimal("1"), rounding=ROUND_CEILING
    )
    return (pasos * PASO_PRECIO_VENTA).quantize(CENTIMO)
