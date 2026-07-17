# Wiring del módulo: arma los casos de uso con sus adaptadores concretos (SQLAlchemy y adaptadores de integración).
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor_a
from app.modules.modulo_c_ventas.application.abrir_caja_usecase import AbrirCajaUseCase
from app.modules.modulo_c_ventas.application.consultar_caja_usecase import ConsultarCajaUseCase
from app.modules.modulo_c_ventas.application.consultar_ventas_usecase import ConsultarVentasUseCase
from app.modules.modulo_c_ventas.application.registrar_venta_usecase import RegistrarVentaUseCase
from app.modules.modulo_c_ventas.infrastructure.adapters.database.sqlalchemy_caja_repository import (
    SqlAlchemyCajaRepository,
)
from app.modules.modulo_c_ventas.infrastructure.adapters.database.sqlalchemy_venta_repository import (
    SqlAlchemyVentaRepository,
)
from app.modules.modulo_c_ventas.infrastructure.adapters.integrations.sqlalchemy_stock_adapter import (
    SqlAlchemyStockAdapter,
)


def abrir_caja_usecase(db: AsyncSession) -> AbrirCajaUseCase:
    return AbrirCajaUseCase(SqlAlchemyCajaRepository(db), contenedor_a.auditoria_usecase(db))


def consultar_caja_usecase(db: AsyncSession) -> ConsultarCajaUseCase:
    return ConsultarCajaUseCase(SqlAlchemyCajaRepository(db))


def registrar_venta_usecase(db: AsyncSession) -> RegistrarVentaUseCase:
    return RegistrarVentaUseCase(
        SqlAlchemyVentaRepository(db),
        SqlAlchemyCajaRepository(db),
        SqlAlchemyStockAdapter(db),
        contenedor_a.auditoria_usecase(db),
    )


def consultar_ventas_usecase(db: AsyncSession) -> ConsultarVentasUseCase:
    return ConsultarVentasUseCase(SqlAlchemyVentaRepository(db))
