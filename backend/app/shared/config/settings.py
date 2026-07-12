# Configuración global vía variables de entorno (Pydantic Settings). Mínimo indispensable para levantar la app.
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # TODO (cualquier módulo puede añadir aquí variables verdaderamente globales; lo específico de un módulo no va acá)
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://tienda:tienda@localhost:5432/tienda_sistema"
    secret_key: str = "change-me"

    class Config:
        env_file = ".env"


settings = Settings()
