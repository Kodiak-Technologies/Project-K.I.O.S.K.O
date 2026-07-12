# Puerto: contrato para leer/actualizar la fila única de configuración del negocio.
from typing import Protocol

from app.modules.modulo_a_seguridad.domain.entities import ConfiguracionNegocio


class ConfiguracionRepositoryPort(Protocol):
    async def obtener(self) -> ConfiguracionNegocio: ...

    async def actualizar(self, configuracion: ConfiguracionNegocio) -> ConfiguracionNegocio: ...
