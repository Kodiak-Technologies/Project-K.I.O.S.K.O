# Zona horaria del negocio, resuelta de forma tolerante.
#
# `zoneinfo` lee la base de datos IANA del sistema operativo. Windows NO la trae:
# sin el paquete `tzdata` instalado, `ZoneInfo("America/Lima")` levanta
# `ZoneInfoNotFoundError` y cualquier consulta que filtre por fecha responde 500.
# Por eso `tzdata` está declarado como dependencia y, además, acá degradamos a
# UTC con un aviso claro en el log en vez de tumbar el endpoint.
import logging
from datetime import timezone, tzinfo
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.shared.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def zona_negocio(nombre: str | None = None) -> tzinfo:
    """Zona horaria del negocio (`settings.zona_horaria_negocio`)."""
    clave = nombre or settings.zona_horaria_negocio
    try:
        return ZoneInfo(clave)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        logger.error(
            "Zona horaria '%s' no disponible (¿falta el paquete `tzdata`?). "
            "Los rangos de fecha se calcularán en UTC, que puede correr el corte "
            "de día unas horas.",
            clave,
        )
        return timezone.utc
