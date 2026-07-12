# Caso de uso: desactivar o reactivar un usuario (solo ADMIN).
# Desactivar impide el login y revoca sus sesiones, pero NO borra su historial:
# sus ventas y movimientos siguen siendo trazables (FK RESTRICT lo garantiza).
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.domain.ports.sesion_repository_port import SesionRepositoryPort
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class CambiarEstadoUsuarioUseCase:
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
        self, admin: Usuario, usuario_id: int, activo: bool, ip: str, user_agent: str
    ) -> Usuario:
        usuario = await self._usuarios.buscar_por_id(usuario_id)
        if usuario is None or usuario.eliminado:
            raise NoEncontradoError("Usuario no encontrado.")
        if usuario.id == admin.id and not activo:
            raise ValidacionError("No puedes desactivar tu propia cuenta.")

        anterior = usuario.activo
        usuario.activo = activo
        actualizado = await self._usuarios.actualizar(usuario)
        if not activo:
            await self._sesiones.revocar_todas_de_usuario(usuario_id)  # se le cierra la sesión ya

        await self._auditoria.ejecutar(
            accion="usuario_activado" if activo else "usuario_desactivado",
            entidad="usuarios",
            usuario_id=admin.id, rol=admin.rol_nombre, entidad_id=usuario_id,
            valor_anterior={"activo": anterior}, valor_nuevo={"activo": activo},
            ip=ip, user_agent=user_agent,
        )
        return actualizado
