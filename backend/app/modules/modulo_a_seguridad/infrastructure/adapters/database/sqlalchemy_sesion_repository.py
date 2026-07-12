# Adaptador: implementa SesionRepositoryPort usando SQLAlchemy async.
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import SesionToken
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import SesionModel


def _a_entidad(fila: SesionModel) -> SesionToken:
    return SesionToken(
        id=fila.id,
        usuario_id=fila.usuario_id,
        refresh_token_hash=fila.refresh_token_hash,
        ip=fila.ip,
        user_agent=fila.user_agent,
        expira_en=fila.expira_en,
        revocada=fila.revocada,
        created_at=fila.created_at,
    )


class SqlAlchemySesionRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def crear(self, sesion: SesionToken) -> SesionToken:
        fila = SesionModel(
            usuario_id=sesion.usuario_id,
            refresh_token_hash=sesion.refresh_token_hash,
            ip=sesion.ip,
            user_agent=sesion.user_agent,
            expira_en=sesion.expira_en,
        )
        self._db.add(fila)
        await self._db.flush()
        return _a_entidad(fila)

    async def buscar_por_hash(self, refresh_token_hash: str) -> SesionToken | None:
        resultado = await self._db.execute(
            select(SesionModel).where(SesionModel.refresh_token_hash == refresh_token_hash)
        )
        fila = resultado.scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def revocar(self, sesion_id: int) -> None:
        await self._db.execute(
            update(SesionModel).where(SesionModel.id == sesion_id).values(revocada=True)
        )

    async def revocar_todas_de_usuario(self, usuario_id: int) -> None:
        await self._db.execute(
            update(SesionModel).where(SesionModel.usuario_id == usuario_id).values(revocada=True)
        )
