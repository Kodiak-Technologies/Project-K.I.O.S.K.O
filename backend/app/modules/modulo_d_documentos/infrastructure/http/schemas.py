from datetime import datetime

from pydantic import BaseModel, Field


class BoletaResponse(BaseModel):
    id: int
    venta_id: int
    numero: str
    total: float
    emitida_en: datetime | None
    url_pdf: str | None

    @classmethod
    def desde_entidad(cls, b) -> "BoletaResponse":
        return cls(
            id=b.id,
            venta_id=b.venta_id,
            numero=b.numero,
            total=b.total,
            emitida_en=b.emitida_en,
            url_pdf=b.url_pdf,
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
    numero_ventas: int
    ticket_promedio: float
    top_productos: list[TopProductoResponse]

    @classmethod
    def desde_entidad(cls, r) -> "ReporteResumenResponse":
        return cls(
            desde=r.desde,
            hasta=r.hasta,
            total_vendido=r.total_vendido,
            numero_ventas=r.numero_ventas,
            ticket_promedio=r.ticket_promedio,
            top_productos=[TopProductoResponse.desde_entidad(p) for p in r.top_productos],
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
