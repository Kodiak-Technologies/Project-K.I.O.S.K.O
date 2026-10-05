from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import require_role
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)
from app.shared.database.session import get_db
from app.shared.config.settings import settings

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
    usuario: Usuario = Depends(require_role("ADMIN")),
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
        mensaje = error.replace(" ", "%20")
        return RedirectResponse(url=f"{settings.frontend_url}?drive=error&mensaje={mensaje}")

    if not code:
        return RedirectResponse(
            url=f"{settings.frontend_url}?drive=error&mensaje=No%20se%20recibi%C3%B3%20c%C3%B3digo%20de%20autorizaci%C3%B3n"
        )

    adapter = GoogleDriveAdapter(token_repository=token_repository)
    token_entity = await adapter.intercambiar_code_por_tokens(code)

    # Normalizar refresh_token
    refresh_token_norm = (token_entity.refresh_token or "").strip()

    existente = await token_repository.obtener_por_proveedor("google_drive")
    if existente:
        existente.access_token = token_entity.access_token
        if refresh_token_norm:
            existente.refresh_token = refresh_token_norm
        existente.token_expiry = token_entity.token_expiry
        await token_repository.actualizar(existente)
    else:
        token_entity.refresh_token = refresh_token_norm
        await token_repository.guardar(token_entity)

    return RedirectResponse(url=f"{settings.frontend_url}?drive=ok")


@router.get("/status")
async def drive_status(
    token_repository: SqlAlchemyOAuthTokenRepository = Depends(_get_token_repository),
    usuario: Usuario = Depends(require_role("ADMIN")),
):
    token = await token_repository.obtener_por_proveedor("google_drive")
    if token is None:
        return {
            "autorizado": False,
            "conectado": False,
            "expirado": False,
            "tiene_refresh_token": False,
            "puede_reconectar": False,
            "token_expiry": None,
            "mensaje": "Google Drive no está conectado.",
        }

    tiene_refresh_token = bool(token.refresh_token and token.refresh_token.strip())
    expirado = token.esta_expirado
    conectado = tiene_refresh_token or (not expirado)
    puede_reconectar = tiene_refresh_token

    return {
        "autorizado": True,
        "conectado": conectado,
        "expirado": expirado,
        "tiene_refresh_token": tiene_refresh_token,
        "puede_reconectar": puede_reconectar,
        "token_expiry": token.token_expiry.isoformat() if token.token_expiry else None,
        "mensaje": None,
    }
