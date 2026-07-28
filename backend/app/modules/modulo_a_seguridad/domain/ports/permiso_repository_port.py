# Puerto: contrato para consultar roles/permisos y reasignar permisos a un rol.
# Los permisos viven en BD (no hardcodeados) para ajustarlos sin redeploy.
from typing import Protocol

from app.modules.modulo_a_seguridad.domain.entities import Permiso, Rol


class PermisoRepositoryPort(Protocol):
    async def listar_roles(self) -> list[Rol]: ...

    async def listar_permisos(self) -> list[Permiso]: ...

    async def permisos_de_rol(self, rol_id: int) -> list[Permiso]: ...

    async def rol_tiene_permiso(self, rol_id: int, codigo_permiso: str) -> bool: ...

    async def reemplazar_permisos_de_rol(self, rol_id: int, codigos: list[str]) -> list[Permiso]: ...
