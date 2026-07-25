# Puerto: wrapper sobre `get_current_user` del Módulo A (opcional).
# Permite que los use cases dependan de una abstracción en lugar de
# `Depends(get_current_user)` directamente, manteniendo el dominio libre de FastAPI.
from abc import ABC, abstractmethod

from app.modules.modulo_a_seguridad.domain.entities import Usuario


class CurrentUserPort(ABC):
    @abstractmethod
    async def actual(self) -> Usuario:
        """Devuelve el usuario autenticado del contexto de la request actual.

        Lanza `NoAutorizadoError` si no hay sesión válida.
        """
