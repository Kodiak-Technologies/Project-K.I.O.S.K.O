from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/drive", tags=["Module D - Google Drive OAuth"])


async def _get_token_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyOAuthTokenRepository(db)


async def _get_drive_adapter(
    token_repository: SqlAlchemyOAuthTokenRepository = Depends(_get_token_repository),
):
    return GoogleDriveAdapter(token_repository=token_repository)


@router.get("/auth-url")
async def obtener_auth_url(
    adapter: GoogleDriveAdapter = Depends(_get_drive_adapter),
):
    url = adapter.obtener_auth_url()
    return {"auth_url": url}


@router.get("/callback")
async def drive_callback(
    code: str | None = Query(None),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    token_repository: SqlAlchemyOAuthTokenRepository = Depends(_get_token_repository),
):
    if error:
        return {"error": f"Google rechazó la autorización: {error}"}
    if not code:
        return {"error": "No se recibió código de autorización. Intenta de nuevo desde GET /drive/auth-url"}

    adapter = GoogleDriveAdapter(token_repository=token_repository)
    token_entity = await adapter.intercambiar_code_por_tokens(code)

    existente = await token_repository.obtener_por_proveedor("google_drive")
    if existente:
        existente.access_token = token_entity.access_token
        existente.refresh_token = token_entity.refresh_token
        existente.token_expiry = token_entity.token_expiry
        await token_repository.actualizar(existente)
    else:
        await token_repository.guardar(token_entity)

    return {"mensaje": "Google Drive autorizado correctamente"}


@router.get("/status")
async def drive_status(
    token_repository: SqlAlchemyOAuthTokenRepository = Depends(_get_token_repository),
):
    token = await token_repository.obtener_por_proveedor("google_drive")
    if token is None:
        return {"autorizado": False, "mensaje": "Google Drive no está autorizado"}
    return {
        "autorizado": True,
        "expirado": token.esta_expirado,
        "token_expiry": token.token_expiry.isoformat() if token.token_expiry else None,
    }
