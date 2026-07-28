# Manejo global de excepciones -> respuestas HTTP. Traduce las excepciones de
# dominio (shared/kernel/exceptions.py) a códigos de estado, para que los casos
# de uso no conozcan HTTP. Tambien captura cualquier excepcion no controlada
# para que el frontend vea el detalle en vez de "Internal Server Error" en
# texto plano (que ademas rompe CORS en el navegador).
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
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
        # NFR-5: include the `code` field when set so the frontend can map
        # it to a user-friendly message via mapErrorCodeToMessage.
        body: dict = {"detail": exc.mensaje}
        if exc.code is not None:
            body["code"] = exc.code
        return JSONResponse(status_code=status, content=body)

    # Pydantic / FastAPI 422: payload del request mal formado.
    @app.exception_handler(RequestValidationError)
    async def _manejar_validacion_request(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Cuando el error viene de un validador propio que levanta ValueError,
        # Pydantic mete la excepción en `ctx["error"]`. Ese objeto NO es
        # serializable a JSON: JSONResponse fallaba dentro del handler y el
        # 422 terminaba saliendo como 500 (p. ej. PATCH /proveedores con un
        # email inválido). Normalizamos `ctx` a texto.
        errores = []
        for error in exc.errors():
            limpio = {clave: valor for clave, valor in error.items() if clave != "ctx"}
            contexto = error.get("ctx")
            if contexto:
                limpio["ctx"] = {c: str(v) for c, v in contexto.items()}
            errores.append(limpio)
        return JSONResponse(
            status_code=422, content=jsonable_encoder({"detail": errores})
        )

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
