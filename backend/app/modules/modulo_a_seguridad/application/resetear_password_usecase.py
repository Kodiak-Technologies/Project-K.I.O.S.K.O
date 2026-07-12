# Caso de uso: el ADMIN resetea la contraseña de otro usuario (PATCH /usuarios/{id}/password).
# Puede forzar el cambio en el próximo ingreso. Revoca las sesiones del usuario afectado.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.domain.ports.password_hasher_port import PasswordHasherPort
from app.modules.modulo_a_seguridad.domain.ports.sesion_repository_port import SesionRepositoryPort
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.modules.modulo_a_seguridad.domain.value_objects import PasswordPlano
from app.shared.kernel.exceptions import NoEncontradoError


class ResetearPasswordUseCase:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        sesion_repo: SesionRepositoryPort,
        hasher: PasswordHasherPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._usuarios = usuario_repo
        self._sesiones = sesion_repo
        self._hasher = hasher
        self._auditoria = auditoria

    async def ejecutar(
        self,
        admin: Usuario,
        usuario_id: int,
        password_nueva: str,
        forzar_cambio: bool,
        ip: str,
        user_agent: str,
    ) -> None:
        usuario = await self._usuarios.buscar_por_id(usuario_id)
        if usuario is None or usuario.eliminado:
            raise NoEncontradoError("Usuario no encontrado.")
        PasswordPlano(password_nueva)

        usuario.password_hash = self._hasher.hashear(password_nueva)
        usuario.debe_cambiar_password = forzar_cambio
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        await self._usuarios.actualizar(usuario)
        await self._sesiones.revocar_todas_de_usuario(usuario_id)

        await self._auditoria.ejecutar(
            accion="password_reseteada", entidad="usuarios",
            usuario_id=admin.id, rol=admin.rol_nombre, entidad_id=usuario_id,
            ip=ip, user_agent=user_agent,
        )
