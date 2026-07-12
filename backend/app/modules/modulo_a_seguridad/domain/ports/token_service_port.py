# Puerto: contrato para emitir/validar tokens de sesión. La implementación concreta (JWT) vive en infrastructure.
from typing import Any, Protocol


class TokenServicePort(Protocol):
    def crear_access_token(self, usuario_id: int, username: str, rol: str) -> str: ...

    def decodificar_access_token(self, token: str) -> dict[str, Any]:
        """Devuelve los claims si el token es válido; lanza NoAutorizadoError si no."""
        ...

    def generar_refresh_token(self) -> str:
        """Token opaco aleatorio (no JWT). Se entrega al cliente; en BD solo va su hash."""
        ...

    def hashear_refresh_token(self, token: str) -> str:
        """Hash determinístico (SHA-256) para poder buscar la sesión por hash."""
        ...
