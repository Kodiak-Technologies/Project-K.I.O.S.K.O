from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.application.generar_boleta_usecase import GenerarBoletaUseCase
from app.modules.modulo_d_documentos.application.subir_boleta_drive_usecase import SubirBoletaDriveUseCase
from app.modules.modulo_d_documentos.application.generar_reporte_ventas_usecase import GenerarReporteVentasUseCase
from app.modules.modulo_d_documentos.application.generar_reporte_mas_vendidos_usecase import GenerarReporteMasVendidosUseCase
from app.modules.modulo_d_documentos.application.exportar_reporte_excel_usecase import ExportarReporteExcelUseCase
from app.modules.modulo_d_documentos.application.enviar_notificacion_usecase import EnviarNotificacionUseCase
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
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import GoogleDriveAdapter
from app.modules.modulo_d_documentos.infrastructure.adapters.external.telegram_notification_adapter import (
    TelegramNotificationAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.excel_generator import ExcelGenerator
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.boleta_png_generator import BoletaPngGenerator

_notificacion_sender = TelegramNotificationAdapter()
_reporte_generator = ExcelGenerator()
_png_generator = BoletaPngGenerator()


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


def generar_boleta_usecase(db: AsyncSession) -> GenerarBoletaUseCase:
    return GenerarBoletaUseCase(
        SqlAlchemyBoletaRepository(db),
        _venta_data_provider,
        _configuracion_provider,
    )


def subir_boleta_drive_usecase(db: AsyncSession) -> SubirBoletaDriveUseCase:
    token_repo = SqlAlchemyOAuthTokenRepository(db)
    drive_adapter = GoogleDriveAdapter(token_repository=token_repo)
    return SubirBoletaDriveUseCase(
        SqlAlchemyBoletaRepository(db),
        drive_adapter,
        SqlAlchemyArchivoDriveRepository(db),
        _png_generator,
        _configuracion_provider,
    )


def generar_reporte_ventas_usecase(db: AsyncSession) -> GenerarReporteVentasUseCase:
    return GenerarReporteVentasUseCase(_venta_data_provider)


def generar_reporte_mas_vendidos_usecase(db: AsyncSession) -> GenerarReporteMasVendidosUseCase:
    return GenerarReporteMasVendidosUseCase(_venta_data_provider)


def exportar_reporte_excel_usecase(db: AsyncSession) -> ExportarReporteExcelUseCase:
    return ExportarReporteExcelUseCase(
        _reporte_generator,
        _venta_data_provider,
        _configuracion_provider,
    )


def enviar_notificacion_usecase(db: AsyncSession) -> EnviarNotificacionUseCase:
    return EnviarNotificacionUseCase(
        _notificacion_sender,
        SqlAlchemyNotificacionRepository(db),
        SqlAlchemyConfigNotificacionesRepository(db),
    )
