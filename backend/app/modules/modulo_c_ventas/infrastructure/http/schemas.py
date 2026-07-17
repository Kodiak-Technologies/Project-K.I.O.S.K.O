# DTOs Pydantic (request/response) del módulo de ventas.
# Contrato con el frontend: docs/FRONTEND_CONTRATOS_API.md (Módulo C).
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.modulo_c_ventas.domain.entities import MetodoPago, TurnoCaja, Venta


# ---------- Caja ----------
class AbrirCajaRequest(BaseModel):
    monto_inicial: float = Field(ge=0)


class TurnoCajaResponse(BaseModel):
    id: int
    abierto_por: str
    monto_inicial: float
    monto_final: float | None
    abierto_en: datetime | None
    cerrado_en: datetime | None
    estado: str
    cerrado_por: str | None = None

    @classmethod
    def desde_entidad(cls, t: TurnoCaja) -> "TurnoCajaResponse":
        return cls(
            id=t.id,
            abierto_por=t.abierto_por,
            monto_inicial=float(t.monto_inicial),
            monto_final=float(t.monto_final) if t.monto_final is not None else None,
            abierto_en=t.abierto_en,
            cerrado_en=t.cerrado_en,
            estado=t.estado,
            cerrado_por=t.cerrado_por,
        )


# ---------- Métodos de pago ----------
class MetodoPagoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    es_efectivo: bool
    activo: bool

    @classmethod
    def desde_entidad(cls, m: MetodoPago) -> "MetodoPagoResponse":
        return cls(
            id=m.id, codigo=m.codigo, nombre=m.nombre,
            es_efectivo=m.es_efectivo, activo=m.activo,
        )


class CrearMetodoPagoRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=50)
    es_efectivo: bool = False


class ActualizarMetodoPagoRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    activo: bool | None = None


# ---------- Ventas ----------
class ItemVentaRequest(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0)


class PagoRequest(BaseModel):
    metodo: str = Field(min_length=1, max_length=20)
    # None en pago único = cubre el total (el backend lo completa).
    monto: float | None = Field(default=None, gt=0)
    # Solo efectivo: con cuánto paga el cliente, para calcular el vuelto.
    monto_recibido: float | None = Field(default=None, gt=0)


class RegistrarVentaRequest(BaseModel):
    items: list[ItemVentaRequest] = Field(min_length=1)
    # Forma completa (RF-20, admite pago mixto). Si no viene, se usa metodo_pago.
    pagos: list[PagoRequest] | None = None
    # Retrocompatibilidad con el contrato original: un solo método por el total.
    metodo_pago: str | None = None

    def pagos_normalizados(self) -> list[dict]:
        if self.pagos:
            return [p.model_dump() for p in self.pagos]
        if self.metodo_pago:
            return [{"metodo": self.metodo_pago, "monto": None, "monto_recibido": None}]
        return []


class ItemVentaResponse(BaseModel):
    producto_id: int
    nombre: str
    precio_unitario: float
    cantidad: int
    cantidad_devuelta: int = 0


class PagoVentaResponse(BaseModel):
    metodo: str
    monto: float
    es_efectivo: bool
    monto_recibido: float | None
    vuelto: float


class VentaResponse(BaseModel):
    id: int
    items: list[ItemVentaResponse]
    total: float
    metodo_pago: str
    pagos: list[PagoVentaResponse]
    vuelto: float
    vendedor: str
    anulada: bool
    estado: str
    turno_id: int
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, v: Venta) -> "VentaResponse":
        return cls(
            id=v.id,
            items=[
                ItemVentaResponse(
                    producto_id=d.producto_id,
                    nombre=d.nombre,
                    precio_unitario=float(d.precio_unitario),
                    cantidad=d.cantidad,
                    cantidad_devuelta=d.cantidad_devuelta,
                )
                for d in v.detalles
            ],
            total=float(v.total),
            metodo_pago=v.metodo_pago,
            pagos=[
                PagoVentaResponse(
                    metodo=p.codigo_metodo,
                    monto=float(p.monto),
                    es_efectivo=p.es_efectivo,
                    monto_recibido=float(p.monto_recibido) if p.monto_recibido is not None else None,
                    vuelto=float(p.vuelto),
                )
                for p in v.pagos
            ],
            vuelto=float(v.vuelto),
            vendedor=v.vendedor,
            anulada=v.anulada,
            estado=v.estado,
            turno_id=v.turno_id,
            created_at=v.created_at,
        )
