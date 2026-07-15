from typing import Protocol


class ConfiguracionProviderPort(Protocol):
    async def obtener(self) -> dict:
        """Retorna la configuración del negocio (nombre_negocio, logo_url, etc.)."""
        ...
