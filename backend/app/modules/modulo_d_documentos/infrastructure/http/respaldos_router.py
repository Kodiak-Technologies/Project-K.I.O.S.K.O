from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
import subprocess
import os

from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_role
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_d_documentos.infrastructure.dependencies import get_respaldo_repository
from app.modules.modulo_d_documentos.infrastructure.http.schemas import RespaldoResponse
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import RespaldoModel
from app.shared.database.session import SessionLocal

from datetime import datetime, timedelta, timezone

BACKUPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts", "backups")

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

    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre = f"tienda_sistema_{timestamp}.dump"
    ruta = os.path.join(BACKUPS_DIR, nombre)

    respaldo = Respaldo(
        id=None,
        archivo_nombre=nombre,
        estado="PENDIENTE",
    )
    resultado = await respaldo_repo.crear(respaldo)

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return RespaldoResponse.desde_entidad(resultado)

    try:
        partes = database_url.replace("postgresql+asyncpg://", "").split("@")
        auth = partes[0].split(":")
        host_db = partes[1].split("/")
        user, password = auth[0], auth[1]
        host_port = host_db[0].split(":")
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        dbname = host_db[1]

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        proc = subprocess.run(
            ["pg_dump", "-h", host, "-p", port, "-U", user, "-d", dbname, "-f", ruta, "--no-owner", "--no-acl"],
            capture_output=True, text=True, env=env, timeout=60,
        )

        if proc.returncode != 0:
            async with SessionLocal() as db:
                r = await db.get(RespaldoModel, resultado.id)
                r.estado = "FALLIDO"
                await db.commit()
            return RespaldoResponse.desde_entidad(resultado)

        tamano = os.path.getsize(ruta)
        async with SessionLocal() as db:
            r = await db.get(RespaldoModel, resultado.id)
            r.estado = "COMPLETADO"
            r.tamano_bytes = tamano
            r.expira_en = datetime.now(timezone.utc) + timedelta(days=30)
            await db.commit()
            await db.refresh(r)

        return RespaldoResponse(
            id=r.id,
            archivo_nombre=r.archivo_nombre,
            tamano_bytes=r.tamano_bytes,
            estado=r.estado,
            generado_en=r.generado_en,
            expira_en=r.expira_en,
        )

    except FileNotFoundError:
        async with SessionLocal() as db:
            r = await db.get(RespaldoModel, resultado.id)
            r.estado = "FALLIDO"
            await db.commit()
        return RespaldoResponse.desde_entidad(resultado)
    except Exception:
        return RespaldoResponse.desde_entidad(resultado)
