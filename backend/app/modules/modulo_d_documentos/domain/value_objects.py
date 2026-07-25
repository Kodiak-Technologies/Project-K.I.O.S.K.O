from enum import Enum


class TipoNotificacion(str, Enum):
    """Tipos de notificación que maneja el sistema."""

    STOCK_BAJO = "STOCK_BAJO"
    APERTURA_CAJA = "APERTURA_CAJA"
    CIERRE_CAJA = "CIERRE_CAJA"
    SOLICITUD_INGRESO = "SOLICITUD_INGRESO"
    SISTEMA = "SISTEMA"


class EstadoRespaldo(str, Enum):
    """Estado de un respaldo de base de datos."""

    PENDIENTE = "PENDIENTE"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"


class NivelDetalle(str, Enum):
    """Nivel de detalle de las notificaciones."""

    BAJO = "BAJO"
    ALTO = "ALTO"


class RutaArchivo:
    """Ruta o URL de un archivo (en Drive o local). No puede estar vacía."""

    def __init__(self, valor: str) -> None:
        if not valor or not valor.strip():
            from app.shared.kernel.exceptions import ValidacionError

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
