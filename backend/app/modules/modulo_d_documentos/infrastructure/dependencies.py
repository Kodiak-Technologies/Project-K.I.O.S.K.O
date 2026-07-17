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
        mock_ventas = {
            1: {"id": 1, "total": 150.00, "metodo_pago": "EFECTIVO", "fecha": "2026-07-15T10:30:00Z"},
            2: {"id": 2, "total": 85.50, "metodo_pago": "TARJETA", "fecha": "2026-07-14T15:45:00Z"},
            3: {"id": 3, "total": 320.00, "metodo_pago": "EFECTIVO", "fecha": "2026-07-13T09:00:00Z"},
        }
        return mock_ventas.get(venta_id)

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        return [
            {"id": 1, "total": 150.00, "fecha": "2026-07-15"},
            {"id": 2, "total": 85.50, "fecha": "2026-07-14"},
            {"id": 3, "total": 320.00, "fecha": "2026-07-13"},
        ]

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        mock_detalles = {
            1: [
                {"nombre": "Arroz 1kg", "cantidad": 2, "precio_unitario": 25.00, "subtotal": 50.00},
                {"nombre": "Aceite 1L", "cantidad": 1, "precio_unitario": 100.00, "subtotal": 100.00},
            ],
            2: [
                {"nombre": "Leche 1L", "cantidad": 3, "precio_unitario": 5.50, "subtotal": 16.50},
                {"nombre": "Pan tajado", "cantidad": 2, "precio_unitario": 8.50, "subtotal": 17.00},
            ],
            3: [
                {"nombre": "Pollo entero", "cantidad": 1, "precio_unitario": 320.00, "subtotal": 320.00},
            ],
        }
        return mock_detalles.get(venta_id, [])


class MockConfiguracionProvider:
    async def obtener(self) -> dict:
        return {"nombre_negocio": "Mi Tienda", "logo_url": ""}


_venta_data_provider = MockVentaDataProvider()
_configuracion_provider = MockConfiguracionProvider()


def get_venta_data_provider():
    return _venta_data_provider


def get_configuracion_provider():
    return _configuracion_provider
