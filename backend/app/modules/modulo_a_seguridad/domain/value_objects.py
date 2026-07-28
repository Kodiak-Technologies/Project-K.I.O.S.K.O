# Value objects del dominio de seguridad: validan su formato al construirse.
import re
from dataclasses import dataclass

from app.shared.kernel.exceptions import ValidacionError

_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")


@dataclass(frozen=True)
class Username:
    """Alias de acceso: minúsculas, números y guion bajo, 3-30 caracteres (ej. 'vendedor1')."""

    valor: str

    def __post_init__(self) -> None:
        if not _USERNAME_RE.match(self.valor):
            raise ValidacionError(
                "El usuario debe tener entre 3 y 30 caracteres: solo minúsculas, números o guion bajo."
            )


@dataclass(frozen=True)
class PasswordPlano:
    """Contraseña en claro recibida en un request. Existe solo para validar la
    política antes de hashear; jamás se persiste."""

    valor: str

    def __post_init__(self) -> None:
        if len(self.valor) < 8:
            raise ValidacionError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r"[A-Za-z]", self.valor) or not re.search(r"\d", self.valor):
            raise ValidacionError("La contraseña debe incluir al menos una letra y un número.")
