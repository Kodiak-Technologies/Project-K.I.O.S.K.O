# Router HTTP: /auth/*. Traduce HTTP <-> casos de uso. Sin lógica de negocio.
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_current_user,
)
from app.modules.modulo_a_seguridad.infrastructure.http.schemas import (
    CambiarPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
async def login(datos: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip, user_agent = contexto_request(request)
    resultado = await contenedor.login_usecase(db).ejecutar(
        datos.username, datos.password, ip, user_agent
    )
    return TokenResponse(
        access_token=resultado.access_token,
        refresh_token=resultado.refresh_token,
        usuario=UsuarioResponse.desde_entidad(resultado.usuario),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(datos: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip, user_agent = contexto_request(request)
    resultado = await contenedor.refresh_usecase(db).ejecutar(datos.refresh_token, ip, user_agent)
    return TokenResponse(
        access_token=resultado.access_token,
        refresh_token=resultado.refresh_token,
        usuario=UsuarioResponse.desde_entidad(resultado.usuario),
    )


@router.post("/logout", status_code=204)
async def logout(
    datos: LogoutRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    await contenedor.logout_usecase(db).ejecutar(usuario, datos.refresh_token, ip, user_agent)


@router.get("/me", response_model=UsuarioResponse)
async def me(usuario: Usuario = Depends(get_current_user)):
    return UsuarioResponse.desde_entidad(usuario)


@router.patch("/password", status_code=204)
async def cambiar_password(
    datos: CambiarPasswordRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    await contenedor.cambiar_password_usecase(db).ejecutar(
        usuario, datos.password_actual, datos.password_nueva, ip, user_agent
    )
