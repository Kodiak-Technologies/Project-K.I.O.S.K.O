import asyncio
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import RespaldoModel
from app.shared.database.session import SessionLocal, engine


BACKUPS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")


async def ejecutar_backup() -> dict:
    os.makedirs(BACKUPS_DIR, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"tienda_sistema_{timestamp}.dump"
    ruta_archivo = os.path.join(BACKUPS_DIR, nombre_archivo)

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL no está configurada")

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

    resultado = subprocess.run(
        [
            "pg_dump",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "-f", ruta_archivo,
            "--no-owner",
            "--no-acl",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    if resultado.returncode != 0:
        raise RuntimeError(f"pg_dump falló: {resultado.stderr}")

    tamano_bytes = os.path.getsize(ruta_archivo)

    async with SessionLocal() as db:
        ahora = datetime.now(timezone.utc)
        respaldo = RespaldoModel(
            archivo_nombre=nombre_archivo,
            tamano_bytes=tamano_bytes,
            estado="COMPLETADO",
            expira_en=ahora + timedelta(days=30),
        )
        db.add(respaldo)
        await db.flush()

        limite = ahora - timedelta(days=30)
        await db.execute(
            delete(RespaldoModel).where(RespaldoModel.generado_en < limite)
        )
        await db.commit()

    return {"nombre": nombre_archivo, "tamano_bytes": tamano_bytes}


async def main() -> None:
    try:
        resultado = await ejecutar_backup()
        print(f"Backup completado: {resultado['nombre']} ({resultado['tamano_bytes']} bytes)")
    except Exception as e:
        print(f"Error en backup: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
