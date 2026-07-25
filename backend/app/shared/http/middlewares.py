# Middlewares transversales: CORS restringido a los orígenes configurados (Vercel en producción)
# y captura de errores no controlados (para que los 500 salgan con headers CORS y traceback en logs).
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.shared.config.settings import settings

logger = logging.getLogger(__name__)


class CapturarErroresMiddleware(BaseHTTPMiddleware):
    """Convierte excepciones no controladas en un 500 JSON.

    Sin esto, la excepción se escapa del stack de middlewares y la respuesta 500
    sale SIN headers CORS: el navegador la reporta como net::ERR_FAILED y el
    frontend no puede mostrar ningún mensaje. Además deja el traceback completo
    en la consola de uvicorn.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Error no controlado en %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno del servidor. Revisa la consola del backend."},
            )


def registrar_middlewares(app: FastAPI) -> None:
    # Orden importa: add_middleware inserta al inicio de la pila, así que CORS
    # (agregado al final) queda por FUERA y añade sus headers también a los 500
    # que devuelve CapturarErroresMiddleware.
    app.add_middleware(CapturarErroresMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
