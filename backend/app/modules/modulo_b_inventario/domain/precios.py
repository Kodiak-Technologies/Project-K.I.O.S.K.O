# Reglas de precio para el ingreso de mercadería (HU-B05/B07).
#
# Por qué existe este módulo: la boleta trae el TOTAL de la línea ("7 esponjas
# — S/ 20"), no el unitario. Derivar uno del otro parece trivial pero tiene una
# trampa que conviene resolver en un solo lugar y testear: la división casi
# nunca da exacta (20/7 = 2.857142…). Si guardáramos el unitario redondeado a 2
# decimales y reconstruyéramos el total como cantidad × unitario, daría 20.02:
# la deuda al proveedor dejaría de cuadrar contra la boleta. Por eso el total es
# la fuente de verdad y el unitario es SIEMPRE derivado, nunca al revés.
#
# El ingreso NO calcula precios de venta. Antes había un `precio_venta_sugerido`
# que aplicaba un margen sobre el costo: se quitó porque terminaba fijando el
# precio de catálogo (y por lo tanto el del punto de venta) sin que nadie lo
# decidiera. El precio de venta se administra únicamente desde el catálogo.
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

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
