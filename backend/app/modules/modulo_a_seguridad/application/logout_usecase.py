# Caso de uso: cerrar sesión (revoca el refresh token) y dejar constancia en bitácora.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.domain.ports.sesion_repository_port import SesionRepositoryPort
from app.modules.modulo_a_seguridad.domain.ports.token_service_port import TokenServicePort


class LogoutUseCase:
    def __init__(
        self,
        sesion_repo: SesionRepositoryPort,
        token_service: TokenServicePort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._sesiones = sesion_repo
        self._tokens = token_service
        self._auditoria = auditoria

    async def ejecutar(self, usuario: Usuario, refresh_token: str, ip: str, user_agent: str) -> None:
        sesion = await self._sesiones.buscar_por_hash(self._tokens.hashear_refresh_token(refresh_token))
        # Solo se puede revocar la sesión propia (evita que alguien cierre sesiones ajenas).
        if sesion is not None and sesion.usuario_id == usuario.id:
            await self._sesiones.revocar(sesion.id)
        await self._auditoria.ejecutar(
            accion="logout", entidad="usuarios",
            usuario_id=usuario.id, rol=usuario.rol_nombre, entidad_id=usuario.id,
            ip=ip, user_agent=user_agent,
        )
