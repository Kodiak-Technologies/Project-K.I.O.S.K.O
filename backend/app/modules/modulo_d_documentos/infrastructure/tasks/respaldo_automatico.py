import logging
from datetime import datetime, timedelta, timezone

from app.shared.database.session import SessionLocal
from app.modules.modulo_d_documentos.domain.entities import Respaldo
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_respaldo_repository import (
    SqlAlchemyRespaldoRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.application.crear_respaldo_usecase import (
    _parsear_database_url,
    _generar_dump_sql,
)
from app.shared.config.settings import settings

logger = logging.getLogger(__name__)


async def respaldo_automatico_diario() -> None:
    ahora = datetime.now(timezone.utc)

    # Ejecutar diariamente a las 3:00 AM hora de Perú (UTC-5, sin DST)
    from zoneinfo import ZoneInfo
    hora_peru = datetime.now(ZoneInfo("America/Lima"))
    if hora_peru.hour != 3:
        return

    logger.info("Iniciando respaldo automático diario (3:00 AM)...")

    timestamp = ahora.strftime("%Y%m%d_%H%M%S")
    nombre = f"tienda_sistema_{timestamp}.sql"

    async with SessionLocal() as db:
        repo = SqlAlchemyRespaldoRepository(db)

        respaldo = Respaldo(
            id=None,
            archivo_nombre=nombre,
            estado="PENDIENTE",
            expira_en=ahora + timedelta(days=4),
        )
        respaldo = await repo.crear(respaldo)
        await db.commit()

        database_url = settings.database_url
        if not database_url:
            logger.error("DATABASE_URL no configurada. Respaldo abortado.")
            return

        try:
            db_params = _parsear_database_url(database_url)
            sql_bytes = await _generar_dump_sql(db_params)

            # Subir a Drive
            token_repo = SqlAlchemyOAuthTokenRepository(db)
            drive_adapter = GoogleDriveAdapter(token_repository=token_repo)

            anio = ahora.strftime("%Y")
            mes = ahora.strftime("%m")
            carpeta_drive = f"respaldos/{anio}/{mes}"
            drive_file_id = await drive_adapter.subir(
                archivo_bytes=sql_bytes,
                nombre=nombre,
                carpeta=carpeta_drive,
            )

            respaldo.tamano_bytes = len(sql_bytes)
            respaldo.estado = "COMPLETADO"
            respaldo.drive_file_id = drive_file_id
            respaldo.expira_en = ahora + timedelta(days=4)
            await repo.actualizar(respaldo)
            await db.commit()
            logger.info("Respaldo automático completado: %s (%d bytes).", nombre, len(sql_bytes))

        except Exception as e:
            logger.error("Error durante el respaldo automático: %s", str(e))
            try:
                respaldo.estado = "FALLIDO"
                await repo.actualizar(respaldo)
                await db.commit()
            except Exception:
                logger.error("Error actualizando estado del respaldo a FALLIDO.")


async def limpiar_respaldos_expirados() -> None:
    logger.info("Limpiando respaldos expirados...")
    async with SessionLocal() as db:
        repo = SqlAlchemyRespaldoRepository(db)

        # Obtener expirados antes de eliminar
        expirados = await repo.eliminar_expirados()
        await db.commit()

        # Eliminar archivos de Drive
        if expirados:
            token_repo = SqlAlchemyOAuthTokenRepository(db)
            drive_adapter = GoogleDriveAdapter(token_repository=token_repo)
            for respaldo in expirados:
                if respaldo.drive_file_id:
                    try:
                        await drive_adapter.eliminar(respaldo.drive_file_id)
                        logger.info("Eliminado de Drive: %s", respaldo.archivo_nombre)
                    except Exception as e:
                        logger.error("Error eliminando %s de Drive: %s", respaldo.archivo_nombre, str(e))

    logger.info("Respaldos expirados eliminados: %d.", len(expirados))
