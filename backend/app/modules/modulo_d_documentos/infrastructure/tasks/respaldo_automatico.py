import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone

from app.shared.database.session import SessionLocal
from app.modules.modulo_d_documentos.domain.entities import Respaldo
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_respaldo_repository import (
    SqlAlchemyRespaldoRepository,
)
from app.shared.config.settings import settings

logger = logging.getLogger(__name__)

BACKUPS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "scripts",
    "backups",
)


async def respaldo_automatico_diario() -> None:
    logger.info("Iniciando respaldo automático diario...")
    os.makedirs(BACKUPS_DIR, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre = f"tienda_sistema_{timestamp}.dump"
    ruta = os.path.join(BACKUPS_DIR, nombre)

    async with SessionLocal() as db:
        repo = SqlAlchemyRespaldoRepository(db)

        respaldo = Respaldo(id=None, archivo_nombre=nombre, estado="PENDIENTE")
        respaldo = await repo.crear(respaldo)
        await db.commit()

        database_url = settings.database_url
        if not database_url:
            logger.error("DATABASE_URL no configurada. Respaldo abortado.")
            return

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
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )

            async with SessionLocal() as db_update:
                r = await db_update.get(type(respaldo).__name__, respaldo.id) if respaldo.id else None
                if proc.returncode == 0 and os.path.exists(ruta):
                    tamano = os.path.getsize(ruta)
                    await db_update.execute(
                        __import__("sqlalchemy").text(
                            "UPDATE respaldos SET estado='COMPLETADO', tamano_bytes=:tamano, "
                            "expira_en=:expira WHERE id=:id"
                        ),
                        {"tamano": tamano, "expira": datetime.now(timezone.utc) + timedelta(days=30), "id": respaldo.id},
                    )
                    await db_update.commit()
                    logger.info("Respaldo completado: %s (%d bytes).", nombre, tamano)
                else:
                    await db_update.execute(
                        __import__("sqlalchemy").text("UPDATE respaldos SET estado='FALLIDO' WHERE id=:id"),
                        {"id": respaldo.id},
                    )
                    await db_update.commit()
                    logger.error("Respaldo fallido: %s. stderr: %s", nombre, proc.stderr)

        except Exception as e:
            logger.error("Error durante el respaldo automático: %s", str(e))
            async with SessionLocal() as db_err:
                await db_err.execute(
                    __import__("sqlalchemy").text("UPDATE respaldos SET estado='FALLIDO' WHERE id=:id"),
                    {"id": respaldo.id},
                )
                await db_err.commit()


async def limpiar_respaldos_expirados() -> None:
    logger.info("Limpiando respaldos expirados...")
    async with SessionLocal() as db:
        repo = SqlAlchemyRespaldoRepository(db)
        eliminados = await repo.eliminar_expirados()
        await db.commit()
    logger.info("Respaldos expirados eliminados: %d.", eliminados)
