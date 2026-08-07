import httpx

from app.modules.modulo_d_documentos.domain.ports.notificacion_sender_port import NotificacionSenderPort
from app.shared.config.settings import settings


class TelegramNotificationAdapter(NotificacionSenderPort):
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    async def enviar(self, canal: str, titulo: str, mensaje: str) -> bool:
        if canal != "TELEGRAM":
            return False

        if not self.token or not self.chat_id:
            return False

        url = self.API_URL.format(token=self.token)
        texto = mensaje

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": texto,
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
            )

        return response.status_code == 200
