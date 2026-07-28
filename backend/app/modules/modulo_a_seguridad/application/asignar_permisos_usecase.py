# Caso de uso: reemplazar los permisos de un rol (solo ADMIN). Como los permisos
# viven en BD, el cambio aplica sin redeploy. Queda auditado con antes/después.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Permiso, Usuario
from app.modules.modulo_a_seguridad.domain.ports.permiso_repository_port import (
    PermisoRepositoryPort,
)


class AsignarPermisosUseCase:
    def __init__(self, permiso_repo: PermisoRepositoryPort, auditoria: RegistrarAuditoriaUseCase):
        self._permisos = permiso_repo
        self._auditoria = auditoria

    async def ejecutar(
        self, admin: Usuario, rol_id: int, codigos: list[str], ip: str, user_agent: str
    ) -> list[Permiso]:
        anteriores = [p.codigo for p in await self._permisos.permisos_de_rol(rol_id)]
        nuevos = await self._permisos.reemplazar_permisos_de_rol(rol_id, codigos)

        await self._auditoria.ejecutar(
            accion="permisos_modificados", entidad="roles",
            usuario_id=admin.id, rol=admin.rol_nombre, entidad_id=rol_id,
            valor_anterior={"permisos": anteriores},
            valor_nuevo={"permisos": [p.codigo for p in nuevos]},
            ip=ip, user_agent=user_agent,
        )
        return nuevos
