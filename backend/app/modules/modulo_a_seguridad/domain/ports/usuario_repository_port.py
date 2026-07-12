# Puerto: contrato para persistir/consultar usuarios. Sin dependencias externas.
from typing import Protocol

from app.modules.modulo_a_seguridad.domain.entities import Usuario


class UsuarioRepositoryPort(Protocol):
    async def buscar_por_id(self, usuario_id: int) -> Usuario | None: ...

    async def buscar_por_username(self, username: str) -> Usuario | None:
        """Debe encontrar también usuarios inactivos/borrados: el caso de uso decide qué hacer."""
        ...

    async def listar(self, incluir_eliminados: bool = False) -> list[Usuario]: ...

    async def crear(self, usuario: Usuario) -> Usuario: ...

    async def actualizar(self, usuario: Usuario) -> Usuario:
        """Persiste los campos mutables (nombre, rol, activo, intentos, bloqueo, hash, etc.)."""
        ...
