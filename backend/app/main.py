import asyncio
import logging
from contextlib import asynccontextmanager

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
from app.modules.modulo_b_inventario.infrastructure.http.categorias_router import (
    router as categorias_router,
)
from app.modules.modulo_b_inventario.infrastructure.http.ingresos_router import (
    router as ingresos_router,
)
from app.modules.modulo_b_inventario.infrastructure.http.inventario_movimientos_router import (
    router as inventario_movimientos_router,
)
from app.modules.modulo_b_inventario.infrastructure.http.mermas_router import (
    router as mermas_router,
)
from app.modules.modulo_b_inventario.infrastructure.http.productos_router import (
    router as productos_router,
)
from app.modules.modulo_b_inventario.infrastructure.http.proveedores_router import (
    router as proveedores_router,
)
from app.modules.modulo_b_inventario.infrastructure.http.storage_router import (
    router as storage_router,
)
from app.modules.modulo_c_ventas.application.cierre_automatico_usecase import (
    CierreAutomaticoUseCase,
)
from app.modules.modulo_c_ventas.infrastructure.adapters.database.sqlalchemy_caja_repository import (
    SqlAlchemyCajaRepository,
)
from app.modules.modulo_c_ventas.infrastructure.http.caja_router import router as caja_router
from app.modules.modulo_c_ventas.infrastructure.http.fiados_router import router as fiados_router
from app.modules.modulo_c_ventas.infrastructure.http.metodos_pago_router import (
    router as metodos_pago_router,
)
from app.modules.modulo_c_ventas.infrastructure.http.ventas_router import router as ventas_router
from app.shared.database.session import SessionLocal
from app.shared.http.error_handlers import registrar_error_handlers
from app.shared.http.middlewares import registrar_middlewares

logger = logging.getLogger(__name__)


async def _ejecutar_cierre_automatico_background() -> None:
    """Cierre automático de caja como tarea en segundo plano.

    Se lanza DESPUÉS del yield del lifespan para no bloquear el startup del
    servidor si la base de datos está lenta o el pool del Supabase Pooler
    tiene una conexión muerta al momento del arranque. Cualquier error se
    loguea y la app sigue funcionando con normalidad.
    """
    try:
        async with SessionLocal() as db:
            usecase = CierreAutomaticoUseCase(SqlAlchemyCajaRepository(db))
            await usecase.ejecutar()
            await db.commit()
    except Exception as exc:
        logger.error(
            "Cierre automático de caja falló (no afecta el funcionamiento del servidor): %s",
            exc,
            exc_info=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El yield debe ejecutarse sí o sí; nunca debe propagarse una excepción
    # previa porque eso impediría que uvicorn termine de arrancar y deje al
    # server "vivo pero sin aceptar conexiones".
    try:
        yield
    finally:
        # Background task post-startup. Usamos create_task para no bloquear
        # el startup y dar margen a que el pool de conexiones se estabilice.
        asyncio.create_task(_ejecutar_cierre_automatico_background())


app = FastAPI(title="Tienda Sistema API", docs_url="/docs", lifespan=lifespan)

registrar_middlewares(app)
registrar_error_handlers(app)

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(roles_router)
app.include_router(bitacora_router)
app.include_router(configuracion_router)

app.include_router(productos_router)
app.include_router(categorias_router)
app.include_router(ingresos_router)
app.include_router(mermas_router)
app.include_router(proveedores_router)
app.include_router(inventario_movimientos_router)
app.include_router(storage_router)

app.include_router(caja_router)
app.include_router(ventas_router)
app.include_router(metodos_pago_router)
app.include_router(fiados_router)


@app.get("/health", tags=["Infra"])
async def health():
    return {"status": "ok"}
