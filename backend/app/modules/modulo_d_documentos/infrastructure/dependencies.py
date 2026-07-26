from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_notificacion_repository import (
    SqlAlchemyNotificacionRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_config_notificaciones_repository import (
    SqlAlchemyConfigNotificacionesRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_respaldo_repository import (
    SqlAlchemyRespaldoRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.http_venta_data_provider import (
    HttpVentaDataProvider,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.http_configuracion_provider import (
    HttpConfiguracionProvider,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.sql_egresos_data_provider import (
    SqlEgresosDataProvider,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.sql_metodo_pago_provider import (
    SqlMetodoPagoProvider,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.telegram_notification_adapter import (
    TelegramNotificationAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.correo_notification_adapter import (
    CorreoNotificationAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.composite_notification_sender import (
    CompositeNotificationSender,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.excel_generator import (
    ExcelGenerator,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.nota_venta_png_generator import (
    NotaVentaPngGenerator,
)
from app.shared.database.session import get_db

_notificacion_sender = CompositeNotificationSender([
    TelegramNotificationAdapter(),
    CorreoNotificationAdapter(),
])
_reporte_generator = ExcelGenerator()
_png_generator = NotaVentaPngGenerator()
_venta_data_provider = HttpVentaDataProvider()
_configuracion_provider = HttpConfiguracionProvider()


async def get_notificacion_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyNotificacionRepository(db)


async def get_config_notificaciones_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyConfigNotificacionesRepository(db)


async def get_respaldo_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyRespaldoRepository(db)


async def get_oauth_token_repository(db: AsyncSession = Depends(get_db)):
    return SqlAlchemyOAuthTokenRepository(db)


async def get_drive_storage(
    token_repository: SqlAlchemyOAuthTokenRepository = Depends(get_oauth_token_repository),
):
    return GoogleDriveAdapter(token_repository=token_repository)


def get_notificacion_sender():
    return _notificacion_sender


def get_reporte_generator():
    return _reporte_generator


def get_png_generator():
    return _png_generator


def get_venta_data_provider():
    return _venta_data_provider


def get_configuracion_provider():
    return _configuracion_provider


# Egresos y desglose por método de pago salen de la BD real (antes eran mocks
# con montos inventados: 1200/150/80 de egresos y 850/320/180/200 de métodos).
def get_egresos_data_provider(db: AsyncSession = Depends(get_db)):
    """Costo de la mercadería ingresada (solicitudes aprobadas)."""
    return SqlEgresosDataProvider(db)


def get_metodo_pago_provider(db: AsyncSession = Depends(get_db)):
    """Recaudación por método, desde `pagos_venta`."""
    return SqlMetodoPagoProvider(db)
