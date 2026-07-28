# Caso de uso: renovar el access token usando el refresh token (sesión persistente).
# Rotación: cada refresh revoca la sesión anterior y emite una nueva.
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.modulo_a_seguridad.domain.entities import SesionToken, Usuario
from app.modules.modulo_a_seguridad.domain.ports.configuracion_repository_port import (
    ConfiguracionRepositoryPort,
)
from app.modules.modulo_a_seguridad.domain.ports.sesion_repository_port import SesionRepositoryPort
from app.modules.modulo_a_seguridad.domain.ports.token_service_port import TokenServicePort
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.shared.kernel.exceptions import NoAutorizadoError


@dataclass
class ResultadoRefresh:
    usuario: Usuario
    access_token: str
    refresh_token: str


class RefreshTokenUseCase:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        sesion_repo: SesionRepositoryPort,
        configuracion_repo: ConfiguracionRepositoryPort,
        token_service: TokenServicePort,
    ):
        self._usuarios = usuario_repo
        self._sesiones = sesion_repo
        self._configuracion = configuracion_repo
        self._tokens = token_service

    async def ejecutar(self, refresh_token: str, ip: str, user_agent: str) -> ResultadoRefresh:
        ahora = datetime.now(timezone.utc)
        sesion = await self._sesiones.buscar_por_hash(self._tokens.hashear_refresh_token(refresh_token))
        if sesion is None or not sesion.es_valida(ahora):
            raise NoAutorizadoError("Sesión inválida o expirada. Inicia sesión de nuevo.")

        usuario = await self._usuarios.buscar_por_id(sesion.usuario_id)
        if usuario is None or not usuario.puede_iniciar_sesion():
            raise NoAutorizadoError("Sesión inválida o expirada. Inicia sesión de nuevo.")

        # Rotación del refresh token: la sesión vieja muere, nace una nueva.
        await self._sesiones.revocar(sesion.id)
        config = await self._configuracion.obtener()
        nuevo_refresh = self._tokens.generar_refresh_token()
        await self._sesiones.crear(
            SesionToken(
                id=None,
                usuario_id=usuario.id,
                refresh_token_hash=self._tokens.hashear_refresh_token(nuevo_refresh),
                ip=ip,
                user_agent=user_agent,
                expira_en=ahora + timedelta(minutes=config.ttl_para_rol(usuario.rol_nombre)),
            )
        )
        access_token = self._tokens.crear_access_token(usuario.id, usuario.username, usuario.rol_nombre)
        return ResultadoRefresh(usuario=usuario, access_token=access_token, refresh_token=nuevo_refresh)
