# Caso de uso: crear un usuario (solo ADMIN — el router lo garantiza con require_permission).
# No hay auto-registro en el sistema: este es el ÚNICO camino para crear cuentas.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.domain.ports.password_hasher_port import PasswordHasherPort
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.modules.modulo_a_seguridad.domain.value_objects import PasswordPlano, Username
from app.shared.kernel.exceptions import ConflictoError


class CrearUsuarioUseCase:
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
        self,
        admin: Usuario,
        username: str,
        nombre: str,
        password_inicial: str,
        rol_id: int,
        forzar_cambio_password: bool,
        ip: str,
        user_agent: str,
    ) -> Usuario:
        Username(username)  # valida formato
        PasswordPlano(password_inicial)  # valida política

        if await self._usuarios.buscar_por_username(username) is not None:
            raise ConflictoError(f"El usuario '{username}' ya existe.")

        creado = await self._usuarios.crear(
            Usuario(
                id=None,
                username=username,
                nombre=nombre,
                password_hash=self._hasher.hashear(password_inicial),
                rol_id=rol_id,
                activo=True,
                debe_cambiar_password=forzar_cambio_password,
            )
        )
        await self._auditoria.ejecutar(
            accion="usuario_creado", entidad="usuarios",
            usuario_id=admin.id, rol=admin.rol_nombre, entidad_id=creado.id,
            valor_nuevo={"username": creado.username, "nombre": creado.nombre, "rol_id": creado.rol_id},
            ip=ip, user_agent=user_agent,
        )
        return creado
