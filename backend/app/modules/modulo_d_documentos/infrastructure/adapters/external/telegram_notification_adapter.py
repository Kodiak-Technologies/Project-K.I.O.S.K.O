import os

import httpx

from app.modules.modulo_d_documentos.domain.ports.notificacion_sender_port import NotificacionSenderPort


class TelegramNotificationAdapter(NotificacionSenderPort):
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self) -> None:
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    async def enviar(self, canal: str, titulo: str, mensaje: str) -> bool:
        if canal != "TELEGRAM":
            return False

        if not self.token or not self.chat_id:
            return False

        url = self.API_URL.format(token=self.token)
        texto = f"*{titulo}*\n\n{mensaje}"

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
