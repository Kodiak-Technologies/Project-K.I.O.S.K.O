# Entry point de FastAPI: crea la app, registra middlewares/manejadores de error
# y monta los routers de cada módulo.
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

if sys.platform == "win32":
    # El ProactorEventLoop (default en Windows) rompe asyncpg sobre SSL: una
    # conexión caída lanza AttributeError en vez de un error de desconexión y
    # el pool no puede recuperarla. El SelectorEventLoop las cierra limpio.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
from app.modules.modulo_c_ventas.infrastructure.http.metodos_pago_router import (
    router as metodos_pago_router,
)
from app.modules.modulo_c_ventas.infrastructure.http.ventas_router import router as ventas_router
from app.shared.database.session import SessionLocal
from app.shared.http.error_handlers import registrar_error_handlers
from app.shared.http.middlewares import registrar_middlewares

logger = logging.getLogger(__name__)

TAREA_RESPALDO_INTERVALO = 604800  # 7 días (una semana)


async def _ejecutar_tarea_respaldos() -> None:
    from app.modules.modulo_d_documentos.infrastructure.tasks.respaldo_automatico import (
        respaldo_automatico_diario,
        limpiar_respaldos_expirados,
    )
    from app.modules.modulo_d_documentos.infrastructure.tasks.purgar_notificaciones import (
        purgar_notificaciones_antiguas,
    )
    while True:
        try:
            await respaldo_automatico_diario()
            await limpiar_respaldos_expirados()
            await purgar_notificaciones_antiguas()
        except Exception as e:
            logger.error("Error en tarea de respaldos: %s", str(e))
        await asyncio.sleep(TAREA_RESPALDO_INTERVALO)


async def _ejecutar_cierre_automatico_background() -> None:
    """Cierre automático de caja como tarea en segundo plano.

    Se lanza como background task (create_task) durante el startup para no
    bloquear el arranque del servidor si la base de datos está lenta o el
    pool del Supabase Pooler tiene una conexión muerta al momento del
    arranque. Cualquier error se loguea y la app sigue funcionando con
    normalidad.
    """
    try:
        async with SessionLocal() as db:
            try:
                usecase = CierreAutomaticoUseCase(SqlAlchemyCajaRepository(db))
                await usecase.ejecutar()
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.error(
                    "Cierre automático de caja falló (no afecta el funcionamiento del servidor): %s",
                    exc,
                    exc_info=True,
                )
    except Exception as exc:
        # Defensivo: si hasta el context manager falla, logueamos igual para
        # no perder visibilidad, pero sin propagar la excepción.
        logger.error(
            "Cierre automático de caja no se pudo inicializar: %s",
            exc,
            exc_info=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Iniciamos todas las tareas en segundo plano que provienen de ambos lados
    logger.info("Iniciando tareas en segundo plano...")
    
    task_cierre = asyncio.create_task(_ejecutar_cierre_automatico_background())
    
    # Si la tarea de reintentar existe en tu proyecto, la ejecutamos aquí
    task_reintentar = asyncio.create_task(_ejecutar_tarea_reintentar())
    
    task_respaldos = asyncio.create_task(_ejecutar_tarea_respaldos())

    try:
        yield
    finally:
        # Se asegura de cancelar absolutamente todas al apagar el server
        logger.info("Deteniendo tareas en segundo plano...")
        task_cierre.cancel()
        task_reintentar.cancel()
        task_respaldos.cancel()


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

# --- Módulo D (Fabrizio): Documentos ---
from app.modules.modulo_d_documentos.infrastructure.http.notas_venta_router import router as notas_venta_router
from app.modules.modulo_d_documentos.infrastructure.http.reportes_router import router as reportes_router
from app.modules.modulo_d_documentos.infrastructure.http.notificaciones_router import router as notificaciones_router
from app.modules.modulo_d_documentos.infrastructure.http.respaldos_router import router as respaldos_router
from app.modules.modulo_d_documentos.infrastructure.http.drive_router import router as drive_router

app.include_router(notas_venta_router)
app.include_router(reportes_router)
app.include_router(notificaciones_router)
app.include_router(respaldos_router)
app.include_router(drive_router)


@app.get("/health", tags=["Infra"])
async def health():
    return {"status": "ok"}