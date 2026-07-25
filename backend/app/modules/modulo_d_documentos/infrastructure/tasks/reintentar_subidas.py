import logging
from datetime import datetime, timedelta, timezone

from app.shared.database.session import SessionLocal
from app.modules.modulo_d_documentos.infrastructure.adapters.external.http_venta_data_provider import (
    HttpVentaDataProvider,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.http_configuracion_provider import (
    HttpConfiguracionProvider,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.nota_venta_png_generator import (
    NotaVentaPngGenerator,
)
from app.modules.modulo_d_documentos.application.generar_nota_venta_usecase import (
    GenerarNotaVentaUseCase,
)

logger = logging.getLogger(__name__)


async def reintentar_subidas_pendientes() -> None:
    """Reintenta subir notas de venta a Google Drive para ventas recientes.

    Esta tarea se ejecuta periodicamente para asegurar que todas las notas
    de venta sean subidas a Drive, incluso si hubo errores temporales.
    """
    logger.info("Iniciando reintento de subidas a Google Drive...")

    try:
        venta_data = HttpVentaDataProvider()
        configuracion = HttpConfiguracionProvider()
        png_generator = NotaVentaPngGenerator()

        async with SessionLocal() as db:
            token_repo = SqlAlchemyOAuthTokenRepository(db)
            drive_adapter = GoogleDriveAdapter(token_repository=token_repo)

            generar_nota = GenerarNotaVentaUseCase(
                venta_data=venta_data,
                config_data=configuracion,
                png_generator=png_generator,
            )

            try:
                desde = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
                hasta = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                ventas = await venta_data.listar_ventas(desde=desde, hasta=hasta)

                if not ventas:
                    logger.info("No hay ventas recientes para subir.")
                    return

                subidos = 0
                errores = 0

                for venta in ventas:
                    venta_id = venta["id"]
                    try:
                        png_bytes = await generar_nota.ejecutar(venta_id)
                        fecha = venta.get("fecha", "")
                        if hasattr(fecha, "strftime"):
                            fecha = fecha.strftime("%Y-%m-%d")
                        nombre = f"{str(fecha)[:10]}_VENTA-{venta_id}.png"
                        await drive_adapter.subir(
                            archivo_bytes=png_bytes,
                            nombre=nombre,
                            carpeta="Notas de Venta",
                        )
                        subidos += 1
                    except Exception as e:
                        errores += 1
                        logger.debug("Error subiendo venta %d: %s", venta_id, str(e))

                logger.info(
                    "Reintento completado: %d subidos, %d errores de %d totales.",
                    subidos,
                    errores,
                    len(ventas),
                )

            except Exception as e:
                logger.error("Error durante el reintento de subidas: %s", str(e))

    except Exception as e:
        logger.error("Error inicializando reintento de subidas: %s", str(e))
