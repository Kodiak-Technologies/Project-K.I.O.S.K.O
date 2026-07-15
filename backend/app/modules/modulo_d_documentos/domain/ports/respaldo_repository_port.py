from typing import Protocol

from app.modules.modulo_d_documentos.domain.entities import Respaldo


class RespaldoRepositoryPort(Protocol):
    async def crear(self, respaldo: Respaldo) -> Respaldo: ...

    async def listar(self) -> list[Respaldo]:
        """Retorna todos los respaldos, del más reciente al más antiguo."""
        ...

    async def eliminar_expirados(self) -> int:
        """Elimina respaldos con más de 30 días. Retorna cantidad eliminada."""
        ...
