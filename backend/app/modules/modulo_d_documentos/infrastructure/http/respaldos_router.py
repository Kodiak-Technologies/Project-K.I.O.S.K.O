from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.infrastructure.dependencies import get_respaldo_repository
from app.modules.modulo_d_documentos.infrastructure.http.schemas import RespaldoResponse
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import RespaldoModel
from app.shared.database.session import SessionLocal

import os
from datetime import datetime, timezone

BACKUPS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "scripts", "backups")

router = APIRouter(prefix="/respaldos", tags=["Documentos"])


@router.get("", response_model=list[RespaldoResponse])
async def listar_respaldos(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    respaldos = await respaldo_repo.listar()
    return [RespaldoResponse.desde_entidad(r) for r in respaldos]


@router.get("/{respaldo_id}/descargar")
async def descargar_respaldo(
    respaldo_id: int,
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    async with SessionLocal() as db:
        resultado = await db.execute(
            select(RespaldoModel).where(RespaldoModel.id == respaldo_id)
        )
        respaldo = resultado.scalar_one_or_none()
        if not respaldo:
            raise ValueError("Respaldo no encontrado")
        nombre = respaldo.archivo_nombre

    ruta = os.path.join(BACKUPS_DIR, nombre)
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"Archivo {nombre} no existe en disco")
    return FileResponse(
        path=ruta,
        media_type="application/octet-stream",
        filename=nombre,
    )


@router.post("", response_model=RespaldoResponse, status_code=201)
async def crear_respaldo(
    usuario: Usuario = Depends(require_role("ADMIN")),
    respaldo_repo=Depends(get_respaldo_repository),
):
    from app.modules.modulo_d_documentos.domain.entities import Respaldo

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre = f"tienda_sistema_{timestamp}.dump"
    respaldo = Respaldo(
        id=None,
        archivo_nombre=nombre,
        estado="PENDIENTE",
    )
    resultado = await respaldo_repo.crear(respaldo)
    return RespaldoResponse.desde_entidad(resultado)
