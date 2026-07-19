# Manejo global de excepciones -> respuestas HTTP. Traduce las excepciones de
# dominio (shared/kernel/exceptions.py) a códigos de estado, para que los casos
# de uso no conozcan HTTP. Tambien captura cualquier excepcion no controlada
# para que el frontend vea el detalle en vez de "Internal Server Error" en
# texto plano (que ademas rompe CORS en el navegador).
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.kernel.exceptions import (
    ConflictoError,
    CuentaBloqueadaError,
    ErrorDeDominio,
    NoAutorizadoError,
    NoEncontradoError,
    ProhibidoError,
    ValidacionError,
)

logger = logging.getLogger(__name__)

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

    # Pydantic / FastAPI 422: payload del request mal formado.
    @app.exception_handler(RequestValidationError)
    async def _manejar_validacion_request(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # HTTPException generadas por FastAPI (401 del bearer, 404 de rutas, etc.).
    @app.exception_handler(StarletteHTTPException)
    async def _manejar_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # Catch-all: cualquier excepcion que se cuele queda logueada y devuelta
    # como JSON 500, en vez del "Internal Server Error" en texto plano de uvicorn
    # (que ademas sale sin headers CORS y hace creer al navegador que el problema
    # es de CORS cuando en realidad es del backend).
    @app.exception_handler(Exception)
    async def _manejar_excepcion_no_controlada(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Excepcion no controlada en %s %s: %s", request.method, request.url.path, exc
        )
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error interno del servidor: {type(exc).__name__}: {exc}"},
        )
