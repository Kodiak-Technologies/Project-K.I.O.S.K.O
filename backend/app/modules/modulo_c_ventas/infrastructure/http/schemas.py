# DTOs Pydantic (request/response) del módulo de ventas.
# Contrato con el frontend: docs/FRONTEND_CONTRATOS_API.md (Módulo C).
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.modulo_c_ventas.domain.entities import (
    Anulacion,
    ArqueoCaja,
    MetodoPago,
    ResumenCaja,
    TurnoCaja,
    Venta,
)


# ---------- Caja ----------
class AbrirCajaRequest(BaseModel):
    monto_inicial: float = Field(ge=0)


class CerrarCajaRequest(BaseModel):
    monto_final: float = Field(ge=0)
    # Obligatorio solo si el monto difiere de la sugerencia (validado en el caso de uso).
    comentario: str | None = Field(default=None, max_length=500)


class EditarTurnoRequest(BaseModel):
    asignado_a_id: int | None = None
    monto_inicial: float | None = Field(default=None, ge=0)


class ArqueoResponse(BaseModel):
    efectivo_esperado: float
    efectivo_contado: float
    diferencia: float
    comentario: str | None
    total_vendido: float
    totales_por_metodo: dict[str, float]

    @classmethod
    def desde_entidad(cls, a: ArqueoCaja) -> "ArqueoResponse":
        return cls(
            efectivo_esperado=float(a.efectivo_esperado),
            efectivo_contado=float(a.efectivo_contado),
            diferencia=float(a.diferencia),
            comentario=a.comentario,
            total_vendido=float(a.total_vendido),
            totales_por_metodo=a.totales_por_metodo or {},
        )


class TurnoCajaResponse(BaseModel):
    id: int
    abierto_por: str
    monto_inicial: float
    monto_final: float | None
    abierto_en: datetime | None
    cerrado_en: datetime | None
    estado: str
    cerrado_por: str | None = None
    asignado_a_id: int | None = None
    # Presente solo en turnos cerrados: el detalle del arqueo (RF-17).
    arqueo: ArqueoResponse | None = None

    @classmethod
    def desde_entidad(cls, t: TurnoCaja, arqueo: ArqueoCaja | None = None) -> "TurnoCajaResponse":
        return cls(
            id=t.id,
            abierto_por=t.abierto_por,
            monto_inicial=float(t.monto_inicial),
            monto_final=float(t.monto_final) if t.monto_final is not None else None,
            abierto_en=t.abierto_en,
            cerrado_en=t.cerrado_en,
            estado=t.estado,
            cerrado_por=t.cerrado_por,
            asignado_a_id=t.asignado_a_id,
            arqueo=ArqueoResponse.desde_entidad(arqueo) if arqueo else None,
        )


class ResumenCajaResponse(BaseModel):
    turno: TurnoCajaResponse
    efectivo_esperado: float
    desglose: dict[str, float]  # monto_inicial, ventas_efectivo, devoluciones_efectivo
    totales_por_metodo: dict[str, float]
    total_vendido: float
    numero_ventas: int

    @classmethod
    def desde_entidad(cls, r: ResumenCaja) -> "ResumenCajaResponse":
        return cls(
            turno=TurnoCajaResponse.desde_entidad(r.turno),
            efectivo_esperado=float(r.efectivo_esperado),
            desglose={
                "monto_inicial": float(r.monto_inicial),
                "ventas_efectivo": float(r.ventas_efectivo),
                "devoluciones_efectivo": float(r.devoluciones_efectivo),
            },
            totales_por_metodo=r.totales_por_metodo,
            total_vendido=float(r.total_vendido),
            numero_ventas=r.numero_ventas,
        )


# ---------- Anulaciones y devoluciones (el rastro, RF-22) ----------
class AnularVentaRequest(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)


class ItemDevolucionRequest(BaseModel):
    detalle_id: int
    cantidad: int = Field(gt=0)


class DevolverVentaRequest(BaseModel):
    items: list[ItemDevolucionRequest] = Field(min_length=1)
    motivo: str = Field(min_length=1, max_length=500)


class AnulacionResponse(BaseModel):
    id: int
    venta_id: int
    turno_id: int
    tipo: str  # ANULACION | DEVOLUCION
    realizado_por: str
    motivo: str
    monto: float
    efectivo_devuelto: float
    items: list[dict]
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, a: Anulacion) -> "AnulacionResponse":
        return cls(
            id=a.id, venta_id=a.venta_id, turno_id=a.turno_id, tipo=a.tipo,
            realizado_por=a.realizado_por, motivo=a.motivo,
            monto=float(a.monto), efectivo_devuelto=float(a.efectivo_devuelto),
            items=a.items, created_at=a.created_at,
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
    # Modo offline (RF-26): uuid del POS (idempotente) y momento real de la venta.
    client_uuid: str | None = Field(default=None, max_length=36)
    registrada_offline: bool = False
    vendida_en: datetime | None = None

    def pagos_normalizados(self) -> list[dict]:
        if self.pagos:
            return [p.model_dump() for p in self.pagos]
        if self.metodo_pago:
            return [{"metodo": self.metodo_pago, "monto": None, "monto_recibido": None}]
        return []


class ItemVentaResponse(BaseModel):
    # id de la línea: lo usa el frontend para pedir devoluciones parciales.
    id: int | None = None
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
    registrada_offline: bool = False
    vendida_en: datetime | None = None
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, v: Venta) -> "VentaResponse":
        return cls(
            id=v.id,
            items=[
                ItemVentaResponse(
                    id=d.id,
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
            registrada_offline=v.registrada_offline,
            vendida_en=v.vendida_en,
            created_at=v.created_at,
        )


# ---------- Movimientos del turno (rastro del panel de caja, HU-C08) ----------
class MovimientosTurnoResponse(BaseModel):
    """El rastro completo de un turno (modal del panel de caja del ADMIN)."""

    ventas: list[VentaResponse]
    reversos: list[AnulacionResponse]
