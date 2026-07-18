import logging

from app.modules.modulo_d_documentos.domain.ports.notificacion_sender_port import NotificacionSenderPort

logger = logging.getLogger(__name__)


class CompositeNotificationSender(NotificacionSenderPort):
    def __init__(self, adapters: list[NotificacionSenderPort]) -> None:
        self._adapters = adapters

    async def enviar(self, canal: str, titulo: str, mensaje: str) -> bool:
        for adapter in self._adapters:
            try:
                resultado = await adapter.enviar(canal, titulo, mensaje)
                if resultado:
                    return True
            except Exception as e:
                logger.error("Error en adapter %s para canal %s: %s", type(adapter).__name__, canal, e)
        return False
