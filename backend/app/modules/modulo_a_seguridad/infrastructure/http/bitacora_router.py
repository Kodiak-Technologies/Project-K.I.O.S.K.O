# Router HTTP: /bitacora (solo lectura, permiso bitacora.ver — solo ADMIN).
# No existen endpoints de UPDATE/DELETE: la bitácora es inmutable por diseño.
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_permission
from app.modules.modulo_a_seguridad.infrastructure.http.schemas import (
    BitacoraPaginadaResponse,
    RegistroBitacoraResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/bitacora", tags=["Bitácora"])


@router.get("", response_model=BitacoraPaginadaResponse)
async def consultar(
    desde: datetime | None = Query(default=None, description="Fecha/hora inicial (ISO 8601)"),
    hasta: datetime | None = Query(default=None, description="Fecha/hora final (ISO 8601)"),
    usuario_id: int | None = Query(default=None),
    accion: str | None = Query(default=None, description="Ej. login_fallido, venta_registrada"),
    entidad: str | None = Query(default=None, description="Ej. usuarios, ventas, productos"),
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=25, ge=1, le=100),
    admin: Usuario = Depends(require_permission("bitacora.ver")),
    db: AsyncSession = Depends(get_db),
):
    registros, total = await contenedor.consultar_bitacora_usecase(db).ejecutar(
        desde=desde, hasta=hasta, usuario_id=usuario_id, accion=accion, entidad=entidad,
        pagina=pagina, tamano_pagina=tamano_pagina,
    )
    return BitacoraPaginadaResponse(
        registros=[RegistroBitacoraResponse.desde_entidad(r) for r in registros],
        total=total, pagina=pagina, tamano_pagina=tamano_pagina,
    )
