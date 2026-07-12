# Adaptador: implementa PasswordHasherPort usando bcrypt (passlib), cost >= 10.
from passlib.context import CryptContext

_contexto = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)


class BcryptPasswordHasher:
    def hashear(self, password_plano: str) -> str:
        return _contexto.hash(password_plano)

    def verificar(self, password_plano: str, password_hash: str) -> bool:
        return _contexto.verify(password_plano, password_hash)
