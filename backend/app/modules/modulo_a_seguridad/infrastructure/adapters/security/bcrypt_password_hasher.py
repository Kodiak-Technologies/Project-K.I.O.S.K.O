# Adaptador: implementa PasswordHasherPort usando bcrypt directo (cost 12).
# Migrado desde passlib 1.7.4 (incompatible con bcrypt >= 4.0; passlib lee
# bcrypt.__about__.__version__ que fue removido en 4.x). bcrypt directo es
# la opción recomendada por la comunidad y no pierde compatibilidad con
# los hashes ya persistidos (el formato $2b$ es estándar).
import bcrypt

_COST = 12  # Mismo cost que tenía passlib (bcrypt__rounds=12).


class BcryptPasswordHasher:
    def hashear(self, password_plano: str) -> str:
        salt = bcrypt.gensalt(rounds=_COST)
        return bcrypt.hashpw(password_plano.encode("utf-8"), salt).decode("utf-8")

    def verificar(self, password_plano: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(
                password_plano.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            # Hash malformado o de otro algoritmo: nunca coincide.
            return False
