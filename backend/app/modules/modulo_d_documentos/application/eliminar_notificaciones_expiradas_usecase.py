from app.modules.modulo_d_documentos.domain.ports.notificacion_repository_port import NotificacionRepositoryPort


class EliminarNotificacionesExpiradasUseCase:
    def __init__(self, notificacion_repo: NotificacionRepositoryPort) -> None:
        self._notificacion_repo = notificacion_repo

    async def ejecutar(self, dias: int = 30) -> int:
        return await self._notificacion_repo.eliminar_expiradas(dias)
