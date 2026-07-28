# Caso de uso: eliminar un usuario (BORRADO LÓGICO, jamás físico) — solo ADMIN.
# El registro queda con deleted_at/deleted_by y su historial permanece intacto.
from datetime import datetime, timezone

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.domain.ports.sesion_repository_port import SesionRepositoryPort
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class EliminarUsuarioUseCase:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        sesion_repo: SesionRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._usuarios = usuario_repo
        self._sesiones = sesion_repo
        self._auditoria = auditoria

    async def ejecutar(
        self, admin: Usuario, usuario_id: int, motivo: str | None, ip: str, user_agent: str
    ) -> None:
        usuario = await self._usuarios.buscar_por_id(usuario_id)
        if usuario is None or usuario.eliminado:
            raise NoEncontradoError("Usuario no encontrado.")
        if usuario.id == admin.id:
            raise ValidacionError("No puedes eliminar tu propia cuenta.")

        usuario.activo = False
        usuario.deleted_at = datetime.now(timezone.utc)
        usuario.deleted_by = admin.id
        await self._usuarios.actualizar(usuario)
        await self._sesiones.revocar_todas_de_usuario(usuario_id)

        await self._auditoria.ejecutar(
            accion="usuario_eliminado", entidad="usuarios",
            usuario_id=admin.id, rol=admin.rol_nombre, entidad_id=usuario_id,
            valor_anterior={"username": usuario.username, "activo": True},
            motivo=motivo,
            ip=ip, user_agent=user_agent,
        )
