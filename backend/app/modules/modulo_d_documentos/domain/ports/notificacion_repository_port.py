from typing import Protocol

from app.modules.modulo_d_documentos.domain.entities import Notificacion


class NotificacionRepositoryPort(Protocol):
    async def listar(self) -> list[Notificacion]:
        """Retorna todas las notificaciones, no leídas primero."""
        ...

    async def marcar_leida(self, notificacion_id: int) -> Notificacion | None:
        """Marca una notificación como leída. Retorna None si no existe."""
        ...

    async def crear(self, notificacion: Notificacion) -> Notificacion: ...

    async def eliminar_expiradas(self, dias: int = 30) -> int:
        """Elimina notificaciones con más de X días. Retorna cantidad eliminada."""
        ...
