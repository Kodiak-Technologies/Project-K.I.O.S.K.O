from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.domain.entities import ConfigNotificaciones
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import ConfigNotificacionesModel


def _a_entidad(fila: ConfigNotificacionesModel) -> ConfigNotificaciones:
    return ConfigNotificaciones(
        id=fila.id,
        nivel_detalle=fila.nivel_detalle,
        updated_at=fila.updated_at,
    )


class SqlAlchemyConfigNotificacionesRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def obtener(self) -> ConfigNotificaciones:
        resultado = await self._db.execute(
            select(ConfigNotificacionesModel).where(ConfigNotificacionesModel.id == 1)
        )
        fila = resultado.scalar_one_or_none()
        if fila is None:
            fila = ConfigNotificacionesModel(id=1)
            self._db.add(fila)
            await self._db.flush()
            await self._db.refresh(fila)
        return _a_entidad(fila)

    async def actualizar(self, config: ConfigNotificaciones) -> ConfigNotificaciones:
        fila = await self._db.get(ConfigNotificacionesModel, 1)
        if fila is None:
            fila = ConfigNotificacionesModel(id=1)
            self._db.add(fila)
        fila.nivel_detalle = config.nivel_detalle
        await self._db.flush()
        await self._db.refresh(fila)
        return _a_entidad(fila)
