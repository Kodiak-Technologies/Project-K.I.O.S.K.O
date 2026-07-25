from datetime import datetime

from pydantic import BaseModel, Field


class NotaVentaResponse(BaseModel):
    venta_id: int
    identificacion: str
    fecha: str
    total: float
    metodo_pago: str
    estado: str

    @classmethod
    def desde_venta(cls, venta: dict) -> "NotaVentaResponse":
        fecha = venta.get("fecha", "")
        if hasattr(fecha, "strftime"):
            fecha_str = fecha.strftime("%Y-%m-%d %H:%M")
        else:
            fecha_str = str(fecha)
        identificacion = f"{fecha_str[:10]}_VENTA-{venta['id']}"
        return cls(
            venta_id=venta["id"],
            identificacion=identificacion,
            fecha=fecha_str,
            total=float(venta.get("total", 0)),
            metodo_pago=venta.get("metodo_pago", ""),
            estado=venta.get("estado", ""),
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
    usuario_id: int | None
    producto_id: int | None
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, n) -> "NotificacionResponse":
        return cls(
            id=n.id,
            tipo=n.tipo,
            titulo=n.titulo,
            mensaje=n.mensaje,
            leida=n.leida,
            usuario_id=n.usuario_id,
            producto_id=n.producto_id,
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
    usuario_id: int | None = None
    drive_file_id: str | None = None

    @classmethod
    def desde_entidad(cls, r) -> "RespaldoResponse":
        return cls(
            id=r.id,
            archivo_nombre=r.archivo_nombre,
            tamano_bytes=r.tamano_bytes,
            estado=r.estado,
            generado_en=r.generado_en,
            expira_en=r.expira_en,
            usuario_id=getattr(r, "usuario_id", None),
            drive_file_id=getattr(r, "drive_file_id", None),
        )


class ConfigNotificacionesResponse(BaseModel):
    nivel_detalle: str

    @classmethod
    def desde_entidad(cls, c) -> "ConfigNotificacionesResponse":
        return cls(nivel_detalle=c.nivel_detalle)


class ConfigNotificacionesRequest(BaseModel):
    nivel_detalle: str | None = None


class CrearNotificacionRequest(BaseModel):
    tipo: str
    titulo: str
    mensaje: str
    entidad_origen: str | None = None
    entidad_id: str | None = None
    usuario_id: int | None = None
    producto_id: int | None = None


class DescargarNotasRequest(BaseModel):
    desde: str | None = None
    hasta: str | None = None
