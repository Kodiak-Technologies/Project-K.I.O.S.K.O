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


class MockEgresosDataProvider:
    async def obtener_egresos(self, desde: str, hasta: str) -> list[dict]:
        return [
            {"concepto": "Compra mercadería", "monto": 1200.00, "fecha": "2026-07-15", "metodo_pago": "EFECTIVO"},
            {"concepto": "Servicio luz", "monto": 150.00, "fecha": "2026-07-14", "metodo_pago": "TRANSFERENCIA"},
            {"concepto": "Servicio agua", "monto": 80.00, "fecha": "2026-07-13", "metodo_pago": "EFECTIVO"},
        ]

    async def total_egresos(self, desde: str, hasta: str) -> float:
        egresos = await self.obtener_egresos(desde, hasta)
        return sum(e.get("monto", 0) for e in egresos)


class MockMetodoPagoProvider:
    async def desglose_por_metodo(self, desde: str, hasta: str) -> dict[str, float]:
        return {"EFECTIVO": 850.00, "YAPE": 320.00, "PLIN": 180.00, "TARJETA": 200.00}


_egresos_data_provider = MockEgresosDataProvider()
_metodo_pago_provider = MockMetodoPagoProvider()


def get_egresos_data_provider():
    return _egresos_data_provider


def get_metodo_pago_provider():
    return _metodo_pago_provider
