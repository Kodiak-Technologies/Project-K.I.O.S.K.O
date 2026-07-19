import logging

from app.shared.database.session import SessionLocal
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_notificacion_repository import (
    SqlAlchemyNotificacionRepository,
)

logger = logging.getLogger(__name__)


async def purgar_notificaciones_antiguas() -> None:
    logger.info("Purgando notificaciones con más de 30 días...")
    async with SessionLocal() as db:
        repo = SqlAlchemyNotificacionRepository(db)
        eliminadas = await repo.eliminar_expiradas(dias=30)
        await db.commit()
    logger.info("Notificaciones antiguas eliminadas: %d.", eliminadas)
