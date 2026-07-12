# Middlewares transversales: CORS restringido a los orígenes configurados (Vercel en producción).
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.shared.config.settings import settings


def registrar_middlewares(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
