from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    ConfiguracionNegocioModel,
)


class SqlAlchemyConfiguracionProvider:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def obtener(self) -> dict:
        fila = (
            await self._db.execute(
                select(ConfiguracionNegocioModel).where(ConfiguracionNegocioModel.id == 1)
            )
        ).scalar_one_or_none()
        if fila is None:
            return {"nombre_negocio": "Mi Tienda", "logo_url": ""}
        return {
            "nombre_negocio": fila.nombre_negocio,
            "logo_url": fila.logo_url,
        }
