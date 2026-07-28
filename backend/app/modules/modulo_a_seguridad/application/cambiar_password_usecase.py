# Caso de uso: cambio de contraseña PROPIO (PATCH /auth/password).
# Exige la contraseña actual, valida la política y limpia el flag debe_cambiar_password.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.domain.ports.password_hasher_port import PasswordHasherPort
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.modules.modulo_a_seguridad.domain.value_objects import PasswordPlano
from app.shared.kernel.exceptions import NoAutorizadoError


class CambiarPasswordUseCase:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        hasher: PasswordHasherPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._usuarios = usuario_repo
        self._hasher = hasher
        self._auditoria = auditoria

    async def ejecutar(
        self, usuario: Usuario, password_actual: str, password_nueva: str, ip: str, user_agent: str
    ) -> None:
        if not self._hasher.verificar(password_actual, usuario.password_hash):
            raise NoAutorizadoError("La contraseña actual no es correcta.")
        PasswordPlano(password_nueva)  # valida la política (largo, letra+número)

        usuario.password_hash = self._hasher.hashear(password_nueva)
        usuario.debe_cambiar_password = False
        await self._usuarios.actualizar(usuario)
        await self._auditoria.ejecutar(
            accion="password_cambiada", entidad="usuarios",
            usuario_id=usuario.id, rol=usuario.rol_nombre, entidad_id=usuario.id,
            ip=ip, user_agent=user_agent,
        )
