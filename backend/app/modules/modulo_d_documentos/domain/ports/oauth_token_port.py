from typing import Protocol

from app.modules.modulo_d_documentos.domain.entities import OAuthToken


class OAuthTokenRepositoryPort(Protocol):
    async def obtener_por_proveedor(self, proveedor: str) -> OAuthToken | None:
        ...

    async def guardar(self, token: OAuthToken) -> OAuthToken:
        ...

    async def actualizar(self, token: OAuthToken) -> OAuthToken:
        ...
