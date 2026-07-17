# Entry point de FastAPI: crea la app, registra middlewares/manejadores de error
# y monta los routers de cada módulo.
from fastapi import FastAPI

from app.modules.modulo_a_seguridad.infrastructure.http.auth_router import router as auth_router
from app.modules.modulo_a_seguridad.infrastructure.http.bitacora_router import (
    router as bitacora_router,
)
from app.modules.modulo_a_seguridad.infrastructure.http.configuracion_router import (
    router as configuracion_router,
)
from app.modules.modulo_a_seguridad.infrastructure.http.roles_router import router as roles_router
from app.modules.modulo_a_seguridad.infrastructure.http.usuarios_router import (
    router as usuarios_router,
)
from app.shared.http.error_handlers import registrar_error_handlers
from app.shared.http.middlewares import registrar_middlewares

app = FastAPI(title="Tienda Sistema API", docs_url="/docs")

registrar_middlewares(app)
registrar_error_handlers(app)

# --- Módulo A: Seguridad, Accesos, Configuración y Auditoría (Matías) ---
app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(roles_router)
app.include_router(bitacora_router)
app.include_router(configuracion_router)

# --- Módulo D (Fabrizio): Documentos ---
from app.modules.modulo_d_documentos.infrastructure.http.boletas_router import router as boletas_router
from app.modules.modulo_d_documentos.infrastructure.http.reportes_router import router as reportes_router
from app.modules.modulo_d_documentos.infrastructure.http.notificaciones_router import router as notificaciones_router
from app.modules.modulo_d_documentos.infrastructure.http.respaldos_router import router as respaldos_router
from app.modules.modulo_d_documentos.infrastructure.http.drive_router import router as drive_router

app.include_router(boletas_router)
app.include_router(reportes_router)
app.include_router(notificaciones_router)
app.include_router(respaldos_router)
app.include_router(drive_router)

# --- Módulo B (Brayan) y C (Clever): montar sus routers aquí ---


@app.get("/health", tags=["Infra"])
async def health():
    """Usado por Cloud Run para verificar que la app está viva."""
    return {"status": "ok"}
