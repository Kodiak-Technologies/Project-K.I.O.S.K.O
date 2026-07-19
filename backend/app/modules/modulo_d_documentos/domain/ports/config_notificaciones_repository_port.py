from typing import Protocol

from app.modules.modulo_d_documentos.domain.entities import ConfigNotificaciones


class ConfigNotificacionesRepositoryPort(Protocol):
    async def obtener(self) -> ConfigNotificaciones:
        """Retorna la configuración de notificaciones (fila única id=1)."""
        ...

    async def actualizar(self, config: ConfigNotificaciones) -> ConfigNotificaciones:
        """Actualiza la configuración de notificaciones."""
        ...
