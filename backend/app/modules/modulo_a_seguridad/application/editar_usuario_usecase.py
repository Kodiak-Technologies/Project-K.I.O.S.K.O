# Caso de uso: editar nombre y/o rol de un usuario (solo ADMIN). Audita valores antes/después.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.domain.ports.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.shared.kernel.exceptions import NoEncontradoError


class EditarUsuarioUseCase:
    def __init__(self, usuario_repo: UsuarioRepositoryPort, auditoria: RegistrarAuditoriaUseCase):
        self._usuarios = usuario_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        admin: Usuario,
        usuario_id: int,
        nombre: str | None,
        rol_id: int | None,
        ip: str,
        user_agent: str,
    ) -> Usuario:
        usuario = await self._usuarios.buscar_por_id(usuario_id)
        if usuario is None or usuario.eliminado:
            raise NoEncontradoError("Usuario no encontrado.")

        anterior = {"nombre": usuario.nombre, "rol_id": usuario.rol_id}
        if nombre is not None:
            usuario.nombre = nombre
        if rol_id is not None:
            usuario.rol_id = rol_id
        actualizado = await self._usuarios.actualizar(usuario)

        await self._auditoria.ejecutar(
            accion="usuario_editado", entidad="usuarios",
            usuario_id=admin.id, rol=admin.rol_nombre, entidad_id=usuario_id,
            valor_anterior=anterior,
            valor_nuevo={"nombre": actualizado.nombre, "rol_id": actualizado.rol_id},
            ip=ip, user_agent=user_agent,
        )
        return actualizado
