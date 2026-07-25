# Value objects del Módulo B (Catálogo, Inventario y Aprobación de Ingresos).
#
# Convenciones:
#   - Todos `@dataclass(frozen=True)` para garantizar inmutabilidad.
#   - Validación en `__post_init__` levantando `ValidacionError` (mensaje en español).
#   - Las transiciones de estado se validan en la entidad, NO en el VO
#     (D-T04: dominio no conoce HTTP, los VOs solo validan pertenencia al set).
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar


def _validar_pertenencia(valor: str, permitidos: tuple[str, ...], nombre_vo: str) -> None:
    """Helper: levanta `ValidacionError` si el valor no está en el set permitido."""
    # Importación local para no romper el orden de carga en tests.
    from app.shared.kernel.exceptions import ValidacionError

    if valor not in permitidos:
        raise ValidacionError(
            f"{nombre_vo} inválido: '{valor}'. Valores permitidos: {', '.join(permitidos)}"
        )


# =============================================================================
# Estados
# =============================================================================


@dataclass(frozen=True)
class EstadoSolicitud:
    """Estado de una solicitud de ingreso (CU-B04, CU-B05, CU-B06).

    Transiciones válidas (validadas en la entidad `SolicitudIngreso`):
        Pendiente -> Aprobada | Rechazada (terminal)
    """

    valor: str
    PENDIENTE: ClassVar[str] = "Pendiente"
    APROBADA: ClassVar[str] = "Aprobada"
    RECHAZADA: ClassVar[str] = "Rechazada"
    VALORES: ClassVar[tuple[str, ...]] = (PENDIENTE, APROBADA, RECHAZADA)

    def __post_init__(self) -> None:
        _validar_pertenencia(self.valor, self.VALORES, "EstadoSolicitud")

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class EstadoMerma:
    """Estado de una merma (CU-B09, CU-B09b, CU-B09c, D-14).

    Transiciones válidas (validadas en la entidad `Merma`):
        Registrada -> Confirmada | Rechazada (terminal)
    """

    valor: str
    REGISTRADA: ClassVar[str] = "Registrada"
    CONFIRMADA: ClassVar[str] = "Confirmada"
    RECHAZADA: ClassVar[str] = "Rechazada"
    VALORES: ClassVar[tuple[str, ...]] = (REGISTRADA, CONFIRMADA, RECHAZADA)

    def __post_init__(self) -> None:
        _validar_pertenencia(self.valor, self.VALORES, "EstadoMerma")

    def __str__(self) -> str:
        return self.valor


# =============================================================================
# Catálogos cerrados
# =============================================================================


@dataclass(frozen=True)
class MotivoMerma:
    """Motivo de una merma (RF-23). Catálogo cerrado."""

    valor: str
    VENCIMIENTO: ClassVar[str] = "vencimiento"
    ROTURA: ClassVar[str] = "rotura"
    OTRO: ClassVar[str] = "otro"
    VALORES: ClassVar[tuple[str, ...]] = (VENCIMIENTO, ROTURA, OTRO)

    def __post_init__(self) -> None:
        _validar_pertenencia(self.valor, self.VALORES, "MotivoMerma")

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class TipoPago:
    """Tipo de movimiento en `pagos_proveedor` (D-12, D-15)."""

    valor: str
    COMPRA_CREDITO: ClassVar[str] = "compra_credito"
    PAGO: ClassVar[str] = "pago"
    VALORES: ClassVar[tuple[str, ...]] = (COMPRA_CREDITO, PAGO)

    def __post_init__(self) -> None:
        _validar_pertenencia(self.valor, self.VALORES, "TipoPago")

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class TipoMovimiento:
    """Tipo de movimiento de inventario (D-07)."""

    valor: str
    INGRESO: ClassVar[str] = "ingreso"
    MERMA: ClassVar[str] = "merma"
    AJUSTE: ClassVar[str] = "ajuste"
    VENTA: ClassVar[str] = "venta"
    DEVOLUCION: ClassVar[str] = "devolucion"
    VALORES: ClassVar[tuple[str, ...]] = (INGRESO, MERMA, AJUSTE, VENTA, DEVOLUCION)

    def __post_init__(self) -> None:
        _validar_pertenencia(self.valor, self.VALORES, "TipoMovimiento")

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class TipoPrecio:
    """Tipo de precio en `historial_precios` (HU-B11)."""

    valor: str
    VENTA: ClassVar[str] = "venta"
    COMPRA: ClassVar[str] = "compra"
    VALORES: ClassVar[tuple[str, ...]] = (VENTA, COMPRA)

    def __post_init__(self) -> None:
        _validar_pertenencia(self.valor, self.VALORES, "TipoPrecio")

    def __str__(self) -> str:
        return self.valor


# =============================================================================
# Helpers con validación estructural
# =============================================================================


@dataclass(frozen=True)
class CodigoInterno:
    """Código interno autogenerado con formato `PREFIJO-CORRELATIVO` (D-T02).

    Validación: `^[A-Z]{2,5}-\\d{3,6}$` (prefijo 2-5 mayúsculas + guion +
    correlativo de 3-6 dígitos). El prefijo es configurable vía
    `ConfiguracionNegocio.prefijo_codigo_interno`; el VO asume que el caller
    ya pasó el prefijo correcto al construir el código completo.
    """

    valor: str
    PATRON: ClassVar[str] = r"^[A-Z]{2,5}-\d{3,6}$"

    def __post_init__(self) -> None:
        import re

        from app.shared.kernel.exceptions import ValidacionError

        if not re.match(self.PATRON, self.valor):
            raise ValidacionError(
                f"Código interno inválido: '{self.valor}'. "
                f"Formato esperado: PREFIJO-CORRELATIVO (ej. PAP-001)."
            )

    def __str__(self) -> str:
        return self.valor


# =============================================================================
# Helper de resultado para Storage (definido junto al puerto que lo consume)
# =============================================================================


@dataclass(frozen=True)
class StorageResult:
    """Resultado de subir un archivo a Supabase Storage."""

    url: str
    path: str
    filename: str
    mime: str
    size_bytes: int
    expires_at: datetime | None = None  # solo para buckets privados (boletas)
