# DTOs Pydantic (request/response) del módulo de ventas.
# Contrato con el frontend: docs/FRONTEND_CONTRATOS_API.md (Módulo C).
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.modulo_c_ventas.domain.entities import TurnoCaja


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
