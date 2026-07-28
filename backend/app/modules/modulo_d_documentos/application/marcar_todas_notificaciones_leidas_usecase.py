from app.modules.modulo_d_documentos.domain.ports.notificacion_repository_port import NotificacionRepositoryPort


class MarcarTodasNotificacionesLeidasUseCase:
    def __init__(self, notificacion_repo: NotificacionRepositoryPort) -> None:
        self._notificacion_repo = notificacion_repo

    async def ejecutar(self, usuario_id: int) -> int:
        return await self._notificacion_repo.marcar_todas_leidas(usuario_id)
