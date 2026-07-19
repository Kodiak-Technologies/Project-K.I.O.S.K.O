# Value objects del dominio de ventas: MontoDinero, estados y constantes del módulo.
from decimal import ROUND_HALF_UP, Decimal

from app.shared.kernel.exceptions import ValidacionError

DOS_DECIMALES = Decimal("0.01")

# Estados de un turno de caja
TURNO_ABIERTO = "ABIERTO"
TURNO_CERRADO = "CERRADO"

# Estados de una venta
VENTA_COMPLETADA = "COMPLETADA"
VENTA_ANULADA = "ANULADA"
VENTA_DEVUELTA_PARCIAL = "DEVUELTA_PARCIAL"

# Tipos de reverso (rastro que ve la administradora)
REVERSO_ANULACION = "ANULACION"
REVERSO_DEVOLUCION = "DEVOLUCION"

# Códigos de método de pago con significado especial para la caja
METODO_EFECTIVO = "EFECTIVO"
METODO_FIADO = "FIADO"  # descuenta stock pero NO ingresa dinero (RF-28)


def monto_dinero(valor, minimo: Decimal | None = Decimal("0")) -> Decimal:
    """Normaliza un monto a Decimal con 2 decimales; valida que no sea negativo."""
    try:
        monto = Decimal(str(valor)).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
    except Exception as exc:  # InvalidOperation, TypeError
        raise ValidacionError(f"Monto inválido: {valor!r}") from exc
    if minimo is not None and monto < minimo:
        raise ValidacionError("El monto no puede ser negativo.")
    return monto
