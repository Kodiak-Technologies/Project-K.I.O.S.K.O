# Caso de uso: autenticar usuario y emitir tokens (RF-01).
# Reglas: mensaje de error genérico, bloqueo temporal tras N intentos fallidos
# (N y minutos vienen de configuracion_negocio), TTL de refresh según rol,
# y TODO evento (éxito, fallo, bloqueo) queda en bitácora.
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import SesionToken, Usuario
from app.modules.modulo_a_seguridad.domain.ports.configuracion_repository_port import (
    ConfiguracionRepositoryPort,
)
from app.modules.modulo_a_seguridad.domain.ports.password_hasher_port import PasswordHasherPort
from app.modules.modulo_a_seguridad.domain.ports.sesion_repository_port import SesionRepositoryPort
from app.modules.modulo_a_seguridad.domain.ports.token_service_port import TokenServicePort
from app.modules.modulo_a_seguridad.domain.ports.unidad_trabajo_port import UnidadTrabajoPort
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.shared.kernel.exceptions import CuentaBloqueadaError, NoAutorizadoError

MENSAJE_GENERICO = "Usuario o contraseña incorrectos."


@dataclass
class ResultadoLogin:
    usuario: Usuario
    access_token: str
    refresh_token: str


class LoginUseCase:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        sesion_repo: SesionRepositoryPort,
        configuracion_repo: ConfiguracionRepositoryPort,
        hasher: PasswordHasherPort,
        token_service: TokenServicePort,
        auditoria: RegistrarAuditoriaUseCase,
        uow: UnidadTrabajoPort,
    ):
        self._usuarios = usuario_repo
        self._sesiones = sesion_repo
        self._configuracion = configuracion_repo
        self._hasher = hasher
        self._tokens = token_service
        self._auditoria = auditoria
        self._uow = uow

    async def ejecutar(self, username: str, password: str, ip: str, user_agent: str) -> ResultadoLogin:
        ahora = datetime.now(timezone.utc)
        config = await self._configuracion.obtener()
        usuario = await self._usuarios.buscar_por_username(username)

        # Usuario inexistente, borrado o inactivo: mismo mensaje genérico (no revelar cuál campo falló).
        if usuario is None or not usuario.puede_iniciar_sesion():
            await self._auditoria.ejecutar(
                accion="login_fallido", entidad="usuarios",
                usuario_id=usuario.id if usuario else None,
                motivo=f"Intento de login para '{username}' (inexistente o inactivo)",
                ip=ip, user_agent=user_agent,
            )
            # Confirmar ANTES de lanzar: la excepción provoca rollback de la request,
            # pero el evento de bitácora debe sobrevivir.
            await self._uow.confirmar()
            raise NoAutorizadoError(MENSAJE_GENERICO)

        if usuario.esta_bloqueado(ahora):
            await self._auditoria.ejecutar(
                accion="login_rechazado_bloqueo", entidad="usuarios",
                usuario_id=usuario.id, rol=usuario.rol_nombre, entidad_id=usuario.id,
                ip=ip, user_agent=user_agent,
            )
            await self._uow.confirmar()
            raise CuentaBloqueadaError("Cuenta bloqueada temporalmente. Intenta de nuevo más tarde.")

        if not self._hasher.verificar(password, usuario.password_hash):
            usuario.intentos_fallidos += 1
            bloqueada = usuario.intentos_fallidos >= config.max_intentos_login
            if bloqueada:
                usuario.bloqueado_hasta = ahora + timedelta(minutes=config.minutos_bloqueo)
                usuario.intentos_fallidos = 0
            await self._usuarios.actualizar(usuario)
            await self._auditoria.ejecutar(
                accion="login_fallido", entidad="usuarios",
                usuario_id=usuario.id, rol=usuario.rol_nombre, entidad_id=usuario.id,
                ip=ip, user_agent=user_agent,
            )
            if bloqueada:
                await self._auditoria.ejecutar(
                    accion="cuenta_bloqueada", entidad="usuarios",
                    usuario_id=usuario.id, rol=usuario.rol_nombre, entidad_id=usuario.id,
                    motivo=f"Bloqueo de {config.minutos_bloqueo} min tras {config.max_intentos_login} intentos fallidos",
                    ip=ip, user_agent=user_agent,
                )
            # Confirmar: el contador de intentos y los eventos deben persistir pese al 401.
            await self._uow.confirmar()
            raise NoAutorizadoError(MENSAJE_GENERICO)

        # Credenciales correctas: resetear contadores y registrar acceso.
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.ultimo_acceso = ahora
        await self._usuarios.actualizar(usuario)

        access_token = self._tokens.crear_access_token(usuario.id, usuario.username, usuario.rol_nombre)
        refresh_token = self._tokens.generar_refresh_token()
        ttl_minutos = config.ttl_para_rol(usuario.rol_nombre)
        await self._sesiones.crear(
            SesionToken(
                id=None,
                usuario_id=usuario.id,
                refresh_token_hash=self._tokens.hashear_refresh_token(refresh_token),
                ip=ip,
                user_agent=user_agent,
                expira_en=ahora + timedelta(minutes=ttl_minutos),
            )
        )
        await self._auditoria.ejecutar(
            accion="login_exitoso", entidad="usuarios",
            usuario_id=usuario.id, rol=usuario.rol_nombre, entidad_id=usuario.id,
            ip=ip, user_agent=user_agent,
        )
        return ResultadoLogin(usuario=usuario, access_token=access_token, refresh_token=refresh_token)
