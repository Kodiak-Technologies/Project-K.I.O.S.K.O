# Puerto: contrato para persistir/consultar sesiones (refresh tokens).
from typing import Protocol

from app.modules.modulo_a_seguridad.domain.entities import SesionToken


class SesionRepositoryPort(Protocol):
    async def crear(self, sesion: SesionToken) -> SesionToken: ...

    async def buscar_por_hash(self, refresh_token_hash: str) -> SesionToken | None: ...

    async def revocar(self, sesion_id: int) -> None: ...

    async def revocar_todas_de_usuario(self, usuario_id: int) -> None:
        """Cierra todas las sesiones de un usuario (al desactivarlo o resetear su contraseña)."""
        ...
