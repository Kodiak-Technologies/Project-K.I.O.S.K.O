# Excepciones de dominio comunes a todos los módulos.
# Los routers NO las capturan: el manejador global (shared/http/error_handlers.py)
# las traduce a códigos HTTP. Así los casos de uso no conocen HTTP.


class ErrorDeDominio(Exception):
    """Base de todas las excepciones de negocio."""

    def __init__(self, mensaje: str):
        self.mensaje = mensaje
        super().__init__(mensaje)


class NoAutorizadoError(ErrorDeDominio):
    """Credenciales inválidas o token ausente/expirado -> 401."""


class ProhibidoError(ErrorDeDominio):
    """Autenticado pero sin permiso para la acción -> 403."""


class NoEncontradoError(ErrorDeDominio):
    """El recurso no existe (o está borrado lógicamente) -> 404."""


class ConflictoError(ErrorDeDominio):
    """Estado inconsistente, p. ej. username duplicado -> 409."""


class ValidacionError(ErrorDeDominio):
    """Datos que violan reglas de negocio -> 422."""


class CuentaBloqueadaError(ErrorDeDominio):
    """Cuenta bloqueada temporalmente por intentos fallidos -> 423."""
