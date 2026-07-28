from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.domain.entities import OAuthToken
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import OAuthTokenModel


class SqlAlchemyOAuthTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def obtener_por_proveedor(self, proveedor: str) -> OAuthToken | None:
        result = await self._db.execute(
            select(OAuthTokenModel).where(OAuthTokenModel.proveedor == proveedor).limit(1)
        )
        fila = result.scalar_one_or_none()
        if fila is None:
            return None
        return self._to_entity(fila)

    async def guardar(self, token: OAuthToken) -> OAuthToken:
        fila = OAuthTokenModel(
            proveedor=token.proveedor,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_expiry=token.token_expiry,
            usuario_id=token.usuario_id,
        )
        self._db.add(fila)
        await self._db.flush()
        await self._db.refresh(fila)
        return self._to_entity(fila)

    async def actualizar(self, token: OAuthToken) -> OAuthToken:
        result = await self._db.execute(
            select(OAuthTokenModel).where(OAuthTokenModel.id == token.id)
        )
        fila = result.scalar_one()
        fila.access_token = token.access_token
        fila.refresh_token = token.refresh_token
        fila.token_expiry = token.token_expiry
        await self._db.flush()
        await self._db.refresh(fila)
        return self._to_entity(fila)

    def _to_entity(self, fila: OAuthTokenModel) -> OAuthToken:
        return OAuthToken(
            id=fila.id,
            proveedor=fila.proveedor,
            access_token=fila.access_token,
            refresh_token=fila.refresh_token,
            token_expiry=fila.token_expiry,
            usuario_id=fila.usuario_id,
            fecha_creacion=fila.fecha_creacion,
            fecha_actualizacion=fila.fecha_actualizacion,
        )
