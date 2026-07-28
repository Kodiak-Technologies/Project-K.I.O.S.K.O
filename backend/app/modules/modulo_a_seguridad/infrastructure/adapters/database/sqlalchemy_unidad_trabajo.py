# Adaptador: implementa UnidadTrabajoPort con el commit de la sesión SQLAlchemy.
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyUnidadTrabajo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def confirmar(self) -> None:
        await self._db.commit()
