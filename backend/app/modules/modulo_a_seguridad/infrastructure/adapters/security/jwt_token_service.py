# Adaptador: implementa TokenServicePort. Access token = JWT firmado;
# refresh token = cadena opaca aleatoria cuyo hash SHA-256 se guarda en `sesiones`.
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.shared.config.settings import settings
from app.shared.kernel.exceptions import NoAutorizadoError


class JwtTokenService:
    def crear_access_token(self, usuario_id: int, username: str, rol: str) -> str:
        ahora = datetime.now(timezone.utc)
        claims = {
            "sub": str(usuario_id),
            "username": username,
            "rol": rol,
            "type": "access",
            "iat": ahora,
            "exp": ahora + timedelta(minutes=settings.access_token_ttl_minutos),
        }
        return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)

    def decodificar_access_token(self, token: str) -> dict[str, Any]:
        try:
            claims = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError:
            raise NoAutorizadoError("Token inválido o expirado.")
        if claims.get("type") != "access":
            raise NoAutorizadoError("Token inválido o expirado.")
        return claims

    def generar_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)

    def hashear_refresh_token(self, token: str) -> str:
        # SHA-256 (no bcrypt): necesitamos buscar la sesión por hash exacto.
        return hashlib.sha256(token.encode()).hexdigest()
