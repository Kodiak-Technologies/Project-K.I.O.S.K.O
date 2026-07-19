import re
from enum import Enum

from app.shared.kernel.exceptions import ValidacionError

_NUMERO_BOLETA_RE = re.compile(r"^B\d{3}-\d{6}$")


class CanalNotificacion(str, Enum):
    """Canales por los que se pueden enviar notificaciones."""

    CORREO = "CORREO"
    TELEGRAM = "TELEGRAM"
    AMBOS = "AMBOS"


class TipoNotificacion(str, Enum):
    """Tipos de notificación que maneja el sistema."""

    STOCK_BAJO = "STOCK_BAJO"
    CIERRE_CAJA = "CIERRE_CAJA"
    SOLICITUD_INGRESO = "SOLICITUD_INGRESO"
    SISTEMA = "SISTEMA"


class EstadoArchivoDrive(str, Enum):
    """Estado de subida de un archivo a Google Drive."""

    PENDIENTE = "PENDIENTE"
    SUBIDO = "SUBIDO"
    FALLIDO = "FALLIDO"


class EstadoRespaldo(str, Enum):
    """Estado de un respaldo de base de datos."""

    PENDIENTE = "PENDIENTE"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"


class NivelDetalle(str, Enum):
    """Nivel de detalle de las notificaciones."""

    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"


class NumeroBoleta:
    """Correlativo de boleta con formato B001-NNNNNN (3 dígitos de serie, guion, 6 dígitos)."""

    def __init__(self, valor: str) -> None:
        if not _NUMERO_BOLETA_RE.match(valor):
            raise ValidacionError(
                f"Número de boleta inválido: '{valor}'. Formato esperado: B001-000001."
            )
        self.valor = valor

    def __str__(self) -> str:
        return self.valor

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NumeroBoleta):
            return NotImplemented
        return self.valor == other.valor

    def __hash__(self) -> int:
        return hash(self.valor)


class RutaArchivo:
    """Ruta o URL de un archivo (en Drive o local). No puede estar vacía."""

    def __init__(self, valor: str) -> None:
        if not valor or not valor.strip():
            raise ValidacionError("La ruta del archivo no puede estar vacía.")
        self.valor = valor.strip()

    def __str__(self) -> str:
        return self.valor

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RutaArchivo):
            return NotImplemented
        return self.valor == other.valor

    def __hash__(self) -> int:
        return hash(self.valor)
