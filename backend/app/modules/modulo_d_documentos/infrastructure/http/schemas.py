from datetime import datetime

from pydantic import BaseModel, Field


class BoletaResponse(BaseModel):
    id: int
    venta_id: int
    numero: str
    total: float
    emitida_en: datetime | None
    url_pdf: str | None
    cliente_nombre: str | None

    @classmethod
    def desde_entidad(cls, b) -> "BoletaResponse":
        return cls(
            id=b.id,
            venta_id=b.venta_id,
            numero=b.numero,
            total=b.total,
            emitida_en=b.emitida_en,
            url_pdf=b.url_pdf,
            cliente_nombre=b.cliente_nombre,
        )


class TopProductoResponse(BaseModel):
    nombre: str
    cantidad: int
    total: float

    @classmethod
    def desde_entidad(cls, t) -> "TopProductoResponse":
        return cls(nombre=t.nombre, cantidad=t.cantidad, total=t.total)


class ReporteResumenResponse(BaseModel):
    desde: str
    hasta: str
    total_vendido: float
    total_egresos: float
    numero_ventas: int
    ticket_promedio: float
    top_productos: list[TopProductoResponse]
    metodos_pago: dict[str, float]

    @classmethod
    def desde_entidad(cls, r) -> "ReporteResumenResponse":
        return cls(
            desde=r.desde,
            hasta=r.hasta,
            total_vendido=r.total_vendido,
            total_egresos=r.total_egresos,
            numero_ventas=r.numero_ventas,
            ticket_promedio=r.ticket_promedio,
            top_productos=[TopProductoResponse.desde_entidad(p) for p in r.top_productos],
            metodos_pago=r.metodos_pago,
        )


class NotificacionResponse(BaseModel):
    id: int
    tipo: str
    titulo: str
    mensaje: str
    leida: bool
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, n) -> "NotificacionResponse":
        return cls(
            id=n.id,
            tipo=n.tipo,
            titulo=n.titulo,
            mensaje=n.mensaje,
            leida=n.leida,
            created_at=n.created_at,
        )


class MarcarLeidaRequest(BaseModel):
    pass


class RespaldoResponse(BaseModel):
    id: int
    archivo_nombre: str
    tamano_bytes: int
    estado: str
    generado_en: datetime | None
    expira_en: datetime | None

    @classmethod
    def desde_entidad(cls, r) -> "RespaldoResponse":
        return cls(
            id=r.id,
            archivo_nombre=r.archivo_nombre,
            tamano_bytes=r.tamano_bytes,
            estado=r.estado,
            generado_en=r.generado_en,
            expira_en=r.expira_en,
        )


class ArchivoDriveResponse(BaseModel):
    id: int
    boleta_id: int
    archivo_nombre: str
    carpeta: str
    estado: str
    intentos: int
    drive_file_id: str | None
    error_mensaje: str | None
    creado_en: datetime | None
    actualizado_en: datetime | None

    @classmethod
    def desde_entidad(cls, a) -> "ArchivoDriveResponse":
        return cls(
            id=a.id,
            boleta_id=a.boleta_id,
            archivo_nombre=a.archivo_nombre,
            carpeta=a.carpeta,
            estado=a.estado,
            intentos=a.intentos,
            drive_file_id=a.drive_file_id,
            error_mensaje=a.error_mensaje,
            creado_en=a.creado_en,
            actualizado_en=a.actualizado_en,
        )


class ConfigNotificacionesResponse(BaseModel):
    canal_telegram_activo: bool
    canal_correo_activo: bool
    nivel_detalle: str
    telegram_chat_id: str | None
    correo_destino: str | None

    @classmethod
    def desde_entidad(cls, c) -> "ConfigNotificacionesResponse":
        return cls(
            canal_telegram_activo=c.canal_telegram_activo,
            canal_correo_activo=c.canal_correo_activo,
            nivel_detalle=c.nivel_detalle,
            telegram_chat_id=c.telegram_chat_id,
            correo_destino=c.correo_destino,
        )


class ConfigNotificacionesRequest(BaseModel):
    canal_telegram_activo: bool = True
    canal_correo_activo: bool = False
    nivel_detalle: str = "MEDIO"
    telegram_chat_id: str | None = None
    correo_destino: str | None = None


class CrearNotificacionRequest(BaseModel):
    tipo: str
    titulo: str
    mensaje: str
    entidad_origen: str | None = None
    entidad_id: str | None = None
    usuario_id: int | None = None
