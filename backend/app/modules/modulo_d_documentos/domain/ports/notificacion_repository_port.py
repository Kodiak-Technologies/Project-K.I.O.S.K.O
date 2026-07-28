from typing import Protocol

from app.modules.modulo_d_documentos.domain.entities import Notificacion


class NotificacionRepositoryPort(Protocol):
    async def listar(self) -> list[Notificacion]:
        """Retorna todas las notificaciones, no leídas primero."""
        ...

    async def listar_por_usuario(self, usuario_id: int) -> list[Notificacion]:
        """Retorna notificaciones de un usuario específico, no leídas primero."""
        ...

    async def marcar_leida(self, notificacion_id: int) -> Notificacion | None:
        """Marca una notificación como leída. Retorna None si no existe."""
        ...

    async def marcar_todas_leidas(self, usuario_id: int) -> int:
        """Marca todas las no leídas de un usuario como leídas. Retorna cantidad."""
        ...

    async def crear(self, notificacion: Notificacion) -> Notificacion: ...

    async def eliminar_expiradas(self, dias: int = 30) -> int:
        """Elimina notificaciones con más de X días. Retorna cantidad eliminada."""
        ...
