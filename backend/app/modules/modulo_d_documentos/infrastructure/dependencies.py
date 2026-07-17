from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_boleta_repository import (
    SqlAlchemyBoletaRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_archivo_drive_repository import (
    SqlAlchemyArchivoDriveRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_notificacion_repository import (
    SqlAlchemyNotificacionRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_config_notificaciones_repository import (
    SqlAlchemyConfigNotificacionesRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_respaldo_repository import (
    SqlAlchemyRespaldoRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.telegram_notification_adapter import (
    TelegramNotificationAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.excel_generator import (
    ExcelGenerator,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.boleta_png_generator import (
    BoletaPngGenerator,
)
from app.shared.database.session import get_db

_drive_storage = GoogleDriveAdapter()
_notificacion_sender = TelegramNotificationAdapter()
_reporte_generator = ExcelGenerator()
_png_generator = BoletaPngGenerator()


async def get_boleta_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyBoletaRepository(db)


async def get_archivo_drive_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyArchivoDriveRepository(db)


async def get_notificacion_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyNotificacionRepository(db)


async def get_config_notificaciones_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyConfigNotificacionesRepository(db)


async def get_respaldo_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyRespaldoRepository(db)


def get_drive_storage():
    return _drive_storage


def get_notificacion_sender():
    return _notificacion_sender


def get_reporte_generator():
    return _reporte_generator


def get_png_generator():
    return _png_generator


class MockVentaDataProvider:
    async def obtener_venta(self, venta_id: int) -> dict | None:
        return None

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        return []

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        return []


class MockConfiguracionProvider:
    async def obtener(self) -> dict:
        return {"nombre_negocio": "Mi Tienda", "logo_url": ""}


_venta_data_provider = MockVentaDataProvider()
_configuracion_provider = MockConfiguracionProvider()


def get_venta_data_provider():
    return _venta_data_provider


def get_configuracion_provider():
    return _configuracion_provider
