# Puerto: contrato para hashear y verificar contraseñas (implementado con bcrypt en infrastructure).
from typing import Protocol


class PasswordHasherPort(Protocol):
    def hashear(self, password_plano: str) -> str: ...

    def verificar(self, password_plano: str, password_hash: str) -> bool: ...
