import asyncio
import logging

from app.shared.database.session import SessionLocal
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_archivo_drive_repository import (
    SqlAlchemyArchivoDriveRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_boleta_repository import (
    SqlAlchemyBoletaRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.boleta_png_generator import (
    BoletaPngGenerator,
)
from app.modules.modulo_d_documentos.domain.value_objects import EstadoArchivoDrive

logger = logging.getLogger(__name__)

MAX_INTENTOS = 3


async def reintentar_subidas_pendientes() -> None:
    logger.info("Iniciando reintento de subidas pendientes a Drive...")
    async with SessionLocal() as db:
        token_repo = SqlAlchemyOAuthTokenRepository(db)
        drive_adapter = GoogleDriveAdapter(token_repository=token_repo)
        archivo_repo = SqlAlchemyArchivoDriveRepository(db)
        boleta_repo = SqlAlchemyBoletaRepository(db)
        png_gen = BoletaPngGenerator()

        pendientes = await archivo_repo.listar_pendientes()
        reintentados = 0

        for archivo in pendientes:
            if archivo.intentos >= MAX_INTENTOS:
                logger.warning(
                    "Archivo %s alcanzó el máximo de %d intentos. Marcando como FALLIDO.",
                    archivo.archivo_nombre,
                    MAX_INTENTOS,
                )
                archivo.estado = EstadoArchivoDrive.FALLIDO.value
                await archivo_repo.actualizar_estado(archivo)
                continue

            boleta = await boleta_repo.buscar_por_id(archivo.boleta_id)
            if boleta is None:
                logger.warning("Boleta #%s no encontrada para archivo %s.", archivo.boleta_id, archivo.archivo_nombre)
                continue

            try:
                fecha = boleta.emitida_en.strftime("%Y-%m-%d %H:%M") if boleta.emitida_en else ""
                png_bytes = await png_gen.generar(
                    numero=boleta.numero,
                    total=boleta.total,
                    fecha=fecha,
                    productos=[],
                    nombre_negocio="Mi Tienda",
                )

                drive_file_id = await drive_adapter.subir(png_bytes, archivo.archivo_nombre, archivo.carpeta)

                archivo.estado = EstadoArchivoDrive.SUBIDO.value
                archivo.drive_file_id = drive_file_id
                archivo.intentos += 1
                await archivo_repo.actualizar_estado(archivo)

                reintentados += 1
                logger.info("Reintento exitoso para %s.", archivo.archivo_nombre)

            except Exception as e:
                archivo.estado = EstadoArchivoDrive.FALLIDO.value
                archivo.error_mensaje = str(e)
                archivo.intentos += 1
                await archivo_repo.actualizar_estado(archivo)
                logger.warning("Reintento fallido para %s: %s", archivo.archivo_nombre, str(e))

        await db.commit()

    logger.info("Reintento de subidas pendientes completado. %d reintentados.", reintentados)
