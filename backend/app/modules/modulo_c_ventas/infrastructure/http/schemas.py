# DTOs Pydantic (request/response) del módulo de ventas.
# Contrato con el frontend: docs/FRONTEND_CONTRATOS_API.md (Módulo C).
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.modulo_c_ventas.domain.entities import TurnoCaja, Venta


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


# ---------- Ventas ----------
class ItemVentaRequest(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0)


class RegistrarVentaRequest(BaseModel):
    items: list[ItemVentaRequest] = Field(min_length=1)
    metodo_pago: str = "EFECTIVO"


class ItemVentaResponse(BaseModel):
    producto_id: int
    nombre: str
    precio_unitario: float
    cantidad: int
    cantidad_devuelta: int = 0


class VentaResponse(BaseModel):
    id: int
    items: list[ItemVentaResponse]
    total: float
    metodo_pago: str
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
            vendedor=v.vendedor,
            anulada=v.anulada,
            estado=v.estado,
            turno_id=v.turno_id,
            created_at=v.created_at,
        )
