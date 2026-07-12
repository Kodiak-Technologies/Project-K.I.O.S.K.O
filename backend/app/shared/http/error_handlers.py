# Manejo global de excepciones -> respuestas HTTP. Traduce las excepciones de
# dominio (shared/kernel/exceptions.py) a códigos de estado, para que los casos
# de uso no conozcan HTTP.
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.shared.kernel.exceptions import (
    ConflictoError,
    CuentaBloqueadaError,
    ErrorDeDominio,
    NoAutorizadoError,
    NoEncontradoError,
    ProhibidoError,
    ValidacionError,
)

_CODIGOS: list[tuple[type[ErrorDeDominio], int]] = [
    (NoAutorizadoError, 401),
    (ProhibidoError, 403),
    (NoEncontradoError, 404),
    (ConflictoError, 409),
    (ValidacionError, 422),
    (CuentaBloqueadaError, 423),
]


def registrar_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeDominio)
    async def _manejar_error_dominio(request: Request, exc: ErrorDeDominio) -> JSONResponse:
        status = next((codigo for tipo, codigo in _CODIGOS if isinstance(exc, tipo)), 400)
        return JSONResponse(status_code=status, content={"detail": exc.mensaje})
