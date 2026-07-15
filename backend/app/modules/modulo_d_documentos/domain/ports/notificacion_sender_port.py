from typing import Protocol


class NotificacionSenderPort(Protocol):
    async def enviar(self, canal: str, titulo: str, mensaje: str) -> bool:
        """Envía una notificación por el canal indicado. Retorna True si fue exitoso."""
        ...
