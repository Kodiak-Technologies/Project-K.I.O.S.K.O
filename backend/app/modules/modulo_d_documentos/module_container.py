from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.application.generar_reporte_ventas_usecase import GenerarReporteVentasUseCase
from app.modules.modulo_d_documentos.application.generar_reporte_mas_vendidos_usecase import GenerarReporteMasVendidosUseCase
from app.modules.modulo_d_documentos.application.exportar_reporte_excel_usecase import ExportarReporteExcelUseCase
from app.modules.modulo_d_documentos.application.enviar_notificacion_usecase import EnviarNotificacionUseCase
from app.modules.modulo_d_documentos.application.crear_respaldo_usecase import CrearRespaldoUseCase, RestaurarRespaldoUseCase
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
from app.modules.modulo_d_documentos.infrastructure.adapters.external.correo_notification_adapter import (
    CorreoNotificationAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.composite_notification_sender import (
    CompositeNotificationSender,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.excel_generator import ExcelGenerator
from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.nota_venta_png_generator import NotaVentaPngGenerator
from app.modules.modulo_d_documentos.infrastructure.dependencies import (
    _venta_data_provider,
    _configuracion_provider,
    _egresos_data_provider,
    _metodo_pago_provider,
)

_notificacion_sender = CompositeNotificationSender([
    TelegramNotificationAdapter(),
    CorreoNotificationAdapter(),
])
_reporte_generator = ExcelGenerator()
_png_generator = NotaVentaPngGenerator()


def generar_reporte_ventas_usecase(db: AsyncSession) -> GenerarReporteVentasUseCase:
    return GenerarReporteVentasUseCase(_venta_data_provider)


def generar_reporte_mas_vendidos_usecase(db: AsyncSession) -> GenerarReporteMasVendidosUseCase:
    return GenerarReporteMasVendidosUseCase(_venta_data_provider)


def exportar_reporte_excel_usecase(db: AsyncSession) -> ExportarReporteExcelUseCase:
    return ExportarReporteExcelUseCase(
        _reporte_generator,
        _venta_data_provider,
        _configuracion_provider,
        _egresos_data_provider,
    )


def enviar_notificacion_usecase(db: AsyncSession) -> EnviarNotificacionUseCase:
    return EnviarNotificacionUseCase(
        _notificacion_sender,
        SqlAlchemyNotificacionRepository(db),
        SqlAlchemyConfigNotificacionesRepository(db),
    )


def restaurar_respaldo_usecase(db: AsyncSession) -> RestaurarRespaldoUseCase:
    return RestaurarRespaldoUseCase(SqlAlchemyRespaldoRepository(db))
