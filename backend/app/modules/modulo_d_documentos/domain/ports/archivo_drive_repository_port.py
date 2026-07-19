from typing import Protocol

from app.modules.modulo_d_documentos.domain.entities import ArchivoDrive


class ArchivoDriveRepositoryPort(Protocol):
    async def buscar_por_boleta_id(self, boleta_id: int) -> ArchivoDrive | None: ...

    async def crear(self, archivo: ArchivoDrive) -> ArchivoDrive: ...

    async def actualizar_estado(self, archivo: ArchivoDrive) -> ArchivoDrive: ...

    async def listar_pendientes(self) -> list[ArchivoDrive]:
        """Retorna archivos con estado PENDIENTE para reintento."""
        ...
