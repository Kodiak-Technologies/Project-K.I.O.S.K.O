from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.modules.modulo_d_documentos.domain.value_objects import (
    EstadoArchivoDrive,
    EstadoRespaldo,
)


@dataclass
class Boleta:
    """Boleta digital generada para una venta confirmada."""

    id: int | None
    venta_id: int
    numero: str 
    total: float
    emitida_en: datetime | None = None
    url_pdf: str | None = None
    cliente_nombre: str | None = None

    def __post_init__(self) -> None:
        if self.emitida_en is None:
            self.emitida_en = datetime.now(timezone.utc)


@dataclass
class ArchivoDrive:
    """Registro de un archivo subido (o pendiente) a Google Drive."""

    id: int | None
    boleta_id: int
    archivo_nombre: str
    carpeta: str
    estado: str = EstadoArchivoDrive.PENDIENTE.value
    intentos: int = 0
    drive_file_id: str | None = None
    error_mensaje: str | None = None
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None

    def __post_init__(self) -> None:
        ahora = datetime.now(timezone.utc)
        if self.creado_en is None:
            self.creado_en = ahora
        if self.actualizado_en is None:
            self.actualizado_en = ahora

    @property
    def esta_subido(self) -> bool:
        return self.estado == EstadoArchivoDrive.SUBIDO.value

    @property
    def esta_pendiente(self) -> bool:
        return self.estado == EstadoArchivoDrive.PENDIENTE.value


@dataclass
class Notificacion:
    """Notificación del sistema para un usuario."""

    id: int | None
    tipo: str
    titulo: str
    mensaje: str
    leida: bool = False
    entidad_origen: str | None = None
    entidad_id: str | None = None
    usuario_id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def marcar_leida(self) -> None:
        self.leida = True


@dataclass
class ConfigNotificaciones:
    """Configuración de canales de notificación (fila única id=1)."""

    id: int = 1
    canal_telegram_activo: bool = True
    canal_correo_activo: bool = False
    nivel_detalle: str = "MEDIO"
    telegram_chat_id: str | None = None
    correo_destino: str | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


@dataclass
class Respaldo:
    """Registro de una copia de seguridad de la base de datos."""

    id: int | None
    archivo_nombre: str
    tamano_bytes: int = 0
    estado: str = EstadoRespaldo.PENDIENTE.value
    generado_en: datetime | None = None
    expira_en: datetime | None = None

    def __post_init__(self) -> None:
        ahora = datetime.now(timezone.utc)
        if self.generado_en is None:
            self.generado_en = ahora
        if self.expira_en is None:
            from datetime import timedelta

            self.expira_en = ahora + timedelta(days=30)

    @property
    def esta_completado(self) -> bool:
        return self.estado == EstadoRespaldo.COMPLETADO.value

    @property
    def expirado(self) -> bool:
        ahora = datetime.now(timezone.utc)
        return self.expira_en is not None and self.expira_en < ahora


@dataclass
class OAuthToken:
    """Token OAuth para acceder a Google Drive."""

    id: int | None
    proveedor: str
    access_token: str
    refresh_token: str
    token_expiry: datetime | None = None
    usuario_id: int | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None

    def __post_init__(self) -> None:
        ahora = datetime.now(timezone.utc)
        if self.fecha_creacion is None:
            self.fecha_creacion = ahora
        if self.fecha_actualizacion is None:
            self.fecha_actualizacion = ahora

    @property
    def esta_expirado(self) -> bool:
        if self.token_expiry is None:
            return True
        return self.token_expiry < datetime.now(timezone.utc)


@dataclass
class TopProducto:
    """Producto en el ranking de más vendidos."""

    nombre: str
    cantidad: int
    total: float


@dataclass
class ResumenReporte:
    """Resumen de ventas para un período dado."""

    desde: str
    hasta: str
    total_vendido: float = 0.0
    total_egresos: float = 0.0
    numero_ventas: int = 0
    ticket_promedio: float = 0.0
    top_productos: list[TopProducto] = field(default_factory=list)
    metodos_pago: dict[str, float] = field(default_factory=dict)

    def calcular_ticket_promedio(self) -> None:
        if self.numero_ventas > 0:
            self.ticket_promedio = self.total_vendido / self.numero_ventas
        else:
            self.ticket_promedio = 0.0
