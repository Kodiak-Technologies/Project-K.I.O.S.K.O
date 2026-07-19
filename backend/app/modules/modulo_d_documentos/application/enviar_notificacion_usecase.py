from app.modules.modulo_d_documentos.domain.entities import ConfigNotificaciones, Notificacion
from app.modules.modulo_d_documentos.domain.ports.notificacion_sender_port import NotificacionSenderPort
from app.modules.modulo_d_documentos.domain.ports.notificacion_repository_port import NotificacionRepositoryPort
from app.modules.modulo_d_documentos.domain.ports.config_notificaciones_repository_port import ConfigNotificacionesRepositoryPort
from app.modules.modulo_d_documentos.domain.value_objects import TipoNotificacion


class EnviarNotificacionUseCase:
    def __init__(
        self,
        notificacion_sender: NotificacionSenderPort,
        notificacion_repo: NotificacionRepositoryPort,
        config_repo: ConfigNotificacionesRepositoryPort,
    ) -> None:
        self._notificacion_sender = notificacion_sender
        self._notificacion_repo = notificacion_repo
        self._config_repo = config_repo

    async def ejecutar(
        self,
        tipo: str,
        titulo: str,
        mensaje: str,
        entidad_origen: str | None = None,
        entidad_id: str | None = None,
        usuario_id: int | None = None,
    ) -> Notificacion:
        config = await self._config_repo.obtener()

        texto_enviar = titulo if config.nivel_detalle == "BAJO" else f"{titulo}\n\n{mensaje}"

        if config.canal_telegram_activo:
            try:
                await self._notificacion_sender.enviar("TELEGRAM", titulo, texto_enviar)
            except Exception:
                pass

        if config.canal_correo_activo:
            try:
                await self._notificacion_sender.enviar("CORREO", titulo, texto_enviar)
            except Exception:
                pass

        notificacion = Notificacion(
            id=None,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            entidad_origen=entidad_origen,
            entidad_id=entidad_id,
            usuario_id=usuario_id,
        )

        return await self._notificacion_repo.crear(notificacion)
