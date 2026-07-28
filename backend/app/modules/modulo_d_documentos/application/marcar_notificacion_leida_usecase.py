from app.modules.modulo_d_documentos.domain.ports.notificacion_repository_port import NotificacionRepositoryPort


class MarcarNotificacionLeidaUseCase:
    def __init__(self, notificacion_repo: NotificacionRepositoryPort) -> None:
        self._notificacion_repo = notificacion_repo

    async def ejecutar(self, notificacion_id: int):
        return await self._notificacion_repo.marcar_leida(notificacion_id)
