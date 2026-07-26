# Wiring del módulo: arma los casos de uso con sus adaptadores concretos (SQLAlchemy y adaptadores de integración).
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor_a
from app.modules.modulo_d_documentos import module_container as contenedor_d
from app.modules.modulo_c_ventas.application.abrir_caja_usecase import AbrirCajaUseCase
from app.modules.modulo_c_ventas.application.anular_venta_usecase import AnularVentaUseCase
from app.modules.modulo_c_ventas.application.editar_turno_usecase import EditarTurnoUseCase
from app.modules.modulo_c_ventas.application.cerrar_caja_usecase import CerrarCajaUseCase
from app.modules.modulo_c_ventas.application.consultar_caja_usecase import ConsultarCajaUseCase
from app.modules.modulo_c_ventas.application.consultar_ventas_usecase import ConsultarVentasUseCase
from app.modules.modulo_c_ventas.application.gestionar_metodos_pago_usecase import (
    GestionarMetodosPagoUseCase,
)
from app.modules.modulo_c_ventas.application.registrar_venta_usecase import RegistrarVentaUseCase
from app.modules.modulo_c_ventas.infrastructure.adapters.database.sqlalchemy_caja_repository import (
    SqlAlchemyCajaRepository,
)
from app.modules.modulo_c_ventas.infrastructure.adapters.database.sqlalchemy_metodo_pago_repository import (
    SqlAlchemyMetodoPagoRepository,
)
from app.modules.modulo_c_ventas.infrastructure.adapters.database.sqlalchemy_venta_repository import (
    SqlAlchemyVentaRepository,
)
from app.modules.modulo_c_ventas.infrastructure.adapters.integrations.sqlalchemy_stock_adapter import (
    SqlAlchemyStockAdapter,
)


def abrir_caja_usecase(db: AsyncSession) -> AbrirCajaUseCase:
    return AbrirCajaUseCase(
        SqlAlchemyCajaRepository(db),
        contenedor_a.auditoria_usecase(db),
        contenedor_d.notificador(db),
    )


def cerrar_caja_usecase(db: AsyncSession) -> CerrarCajaUseCase:
    return CerrarCajaUseCase(
        SqlAlchemyCajaRepository(db),
        contenedor_a.auditoria_usecase(db),
        contenedor_d.notificador(db),
    )


def editar_turno_usecase(db: AsyncSession) -> EditarTurnoUseCase:
    return EditarTurnoUseCase(SqlAlchemyCajaRepository(db))


def consultar_caja_usecase(db: AsyncSession) -> ConsultarCajaUseCase:
    return ConsultarCajaUseCase(
        SqlAlchemyCajaRepository(db),
        SqlAlchemyVentaRepository(db),
    )


def registrar_venta_usecase(db: AsyncSession) -> RegistrarVentaUseCase:
    return RegistrarVentaUseCase(
        SqlAlchemyVentaRepository(db),
        SqlAlchemyCajaRepository(db),
        SqlAlchemyStockAdapter(db),
        SqlAlchemyMetodoPagoRepository(db),
        contenedor_a.auditoria_usecase(db),
        contenedor_d.notificador(db),
    )


def consultar_ventas_usecase(db: AsyncSession) -> ConsultarVentasUseCase:
    return ConsultarVentasUseCase(SqlAlchemyVentaRepository(db))


def gestionar_metodos_pago_usecase(db: AsyncSession) -> GestionarMetodosPagoUseCase:
    return GestionarMetodosPagoUseCase(
        SqlAlchemyMetodoPagoRepository(db), contenedor_a.auditoria_usecase(db)
    )


def anular_venta_usecase(db: AsyncSession) -> AnularVentaUseCase:
    return AnularVentaUseCase(
        SqlAlchemyVentaRepository(db),
        SqlAlchemyCajaRepository(db),
        SqlAlchemyStockAdapter(db),
        contenedor_a.auditoria_usecase(db),
    )
