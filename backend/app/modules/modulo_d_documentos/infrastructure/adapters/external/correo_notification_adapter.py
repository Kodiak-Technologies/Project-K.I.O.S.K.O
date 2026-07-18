import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.modules.modulo_d_documentos.domain.ports.notificacion_sender_port import NotificacionSenderPort
from app.shared.config.settings import settings

logger = logging.getLogger(__name__)


class CorreoNotificationAdapter(NotificacionSenderPort):
    async def enviar(self, canal: str, titulo: str, mensaje: str) -> bool:
        if canal != "CORREO":
            return False

        if not settings.smtp_user or not settings.correo_remitente:
            logger.warning("Correo no configurado: SMTP_USER o CORREO_REMITENTE faltan.")
            return False

        return await asyncio.to_thread(self._enviar_sync, titulo, mensaje)

    def _enviar_sync(self, titulo: str, mensaje: str) -> bool:
        msg = MIMEMultipart()
        msg["From"] = settings.correo_remitente
        msg["To"] = settings.correo_destino
        msg["Subject"] = titulo
        msg.attach(MIMEText(mensaje, "plain", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, int(settings.smtp_port)) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)

        logger.info("Correo enviado a %s: %s", settings.correo_destino, titulo)
        return True
