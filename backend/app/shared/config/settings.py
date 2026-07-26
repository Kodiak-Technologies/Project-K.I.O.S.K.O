# Configuración global vía variables de entorno (Pydantic Settings).
# Solo variables verdaderamente transversales; lo específico de un módulo no va acá.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    database_url: str = "postgresql+asyncpg://tienda:tienda@localhost:5432/tienda_sistema"

    # Zona horaria del negocio. Los reportes agrupan "por día" según ESTA zona:
    # una venta de las 23:55 en Lima pertenece a ese día, no al siguiente en UTC.
    zona_horaria_negocio: str = "America/Lima"

    # Firma de los JWT. En producción viene de Secret Manager, nunca del repo.
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutos: int = 15

    # Orígenes permitidos para CORS (dominio de Vercel en producción), separados por coma.
    cors_origins: str = "http://localhost:5173"

    # Module D: Google Drive (OAuth)
    google_drive_client_id: str = ""
    google_drive_client_secret: str = ""
    google_drive_redirect_uri: str = "http://localhost:8000/drive/callback"
    google_drive_folder_id: str = ""

    # Module D: Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Module D: Correo (SMTP)
    smtp_host: str = ""
    smtp_port: str = ""
    smtp_user: str = ""
    smtp_pass: str = ""
    correo_remitente: str = ""
    correo_destino: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
