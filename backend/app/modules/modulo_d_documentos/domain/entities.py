from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.modules.modulo_d_documentos.domain.value_objects import EstadoRespaldo


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
    producto_id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def marcar_leida(self) -> None:
        self.leida = True


@dataclass
class ConfigNotificaciones:
    """Configuración global de notificaciones (fila única id=1)."""

    id: int = 1
    nivel_detalle: str = "BAJO"
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
    usuario_id: int | None = None
    drive_file_id: str | None = None

    def __post_init__(self) -> None:
        ahora = datetime.now(timezone.utc)
        if self.generado_en is None:
            self.generado_en = ahora
        if self.expira_en is None:
            from datetime import timedelta

            self.expira_en = ahora + timedelta(days=21)

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
    # Lo devuelto en devoluciones PARCIALES del período. `total_vendido` ya es
    # neto de esto; sirve para explicar por qué los cobros por método (que son
    # brutos) suman más que lo vendido.
    total_devuelto: float = 0.0
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


@dataclass
class VentaResumen:
    """Resumen de una venta para notas de venta."""

    id: int
    fecha: datetime
    total: float
    metodo_pago: str
    estado: str
    items: list["ItemVentaResumen"] = field(default_factory=list)
    vendedor: str = ""

    @property
    def fecha_formato(self) -> str:
        return self.fecha.strftime("%Y-%m-%d")

    @property
    def identificacion(self) -> str:
        return f"{self.fecha_formato}_VENTA-{self.id}"


@dataclass
class ItemVentaResumen:
    """Ítem de una venta para notas de venta."""

    nombre: str
    cantidad: int
    precio_unitario: float

    @property
    def subtotal(self) -> float:
        return self.cantidad * self.precio_unitario
