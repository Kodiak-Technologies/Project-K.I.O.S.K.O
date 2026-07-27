# Wiring del módulo: arma los casos de uso con sus adaptadores concretos (SQLAlchemy + Storage).
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor_a
from app.modules.modulo_d_documentos import module_container as contenedor_d
from app.modules.modulo_b_inventario.application.actualizar_producto_usecase import (
    ActualizarProductoUseCase,
)
from app.modules.modulo_b_inventario.application.ajustar_stock_usecase import (
    AjustarStockUseCase,
)
from app.modules.modulo_b_inventario.application.aprobar_ingreso_usecase import (
    AprobarIngresoUseCase,
)
from app.modules.modulo_b_inventario.application.buscar_producto_por_codigo_usecase import (
    BuscarProductoPorCodigoUseCase,
)
from app.modules.modulo_b_inventario.application.buscar_producto_por_nombre_usecase import (
    BuscarProductoPorNombreUseCase,
)
from app.modules.modulo_b_inventario.application.cambiar_precio_usecase import (
    CambiarPrecioUseCase,
)
from app.modules.modulo_b_inventario.application.crear_categoria_usecase import (
    CrearCategoriaUseCase,
)
from app.modules.modulo_b_inventario.application.crear_producto_usecase import (
    CrearProductoUseCase,
)
from app.modules.modulo_b_inventario.application.crear_proveedor_usecase import (
    CrearProveedorUseCase,
)
from app.modules.modulo_b_inventario.application.editar_categoria_usecase import (
    EditarCategoriaUseCase,
)
from app.modules.modulo_b_inventario.application.editar_ingreso_usecase import (
    EditarIngresoUseCase,
)
from app.modules.modulo_b_inventario.application.editar_producto_usecase import (
    EditarProductoUseCase,
)
from app.modules.modulo_b_inventario.application.eliminar_producto_usecase import (
    EliminarProductoUseCase,
)
from app.modules.modulo_b_inventario.application.editar_proveedor_usecase import (
    EditarProveedorUseCase,
)
from app.modules.modulo_b_inventario.application.listar_historial_precios_usecase import (
    ListarHistorialPreciosUseCase,
)
from app.modules.modulo_b_inventario.application.listar_ingresos_usecase import (
    ListarIngresosUseCase,
)
from app.modules.modulo_b_inventario.application.listar_movimientos_inventario_usecase import (
    ListarMovimientosInventarioUseCase,
)
from app.modules.modulo_b_inventario.application.listar_pagos_proveedor_usecase import (
    ListarPagosProveedorUseCase,
)
from app.modules.modulo_b_inventario.application.listar_productos_por_reponer_usecase import (
    ListarProductosPorReponerUseCase,
)
from app.modules.modulo_b_inventario.application.listar_productos_usecase import (
    ListarProductosUseCase,
)
from app.modules.modulo_b_inventario.application.listar_proveedores_usecase import (
    ListarProveedoresUseCase,
)
from app.modules.modulo_b_inventario.application.rechazar_ingreso_usecase import (
    RechazarIngresoUseCase,
)
from app.modules.modulo_b_inventario.application.registrar_compra_credito_usecase import (
    RegistrarCompraCreditoUseCase,
)
from app.modules.modulo_b_inventario.application.registrar_ingreso_usecase import (
    RegistrarIngresoUseCase,
)
from app.modules.modulo_b_inventario.application.registrar_pago_proveedor_usecase import (
    RegistrarPagoProveedorUseCase,
)
from app.modules.modulo_b_inventario.application.subir_archivo_usecase import (
    SubirArchivoUseCase,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_categoria_repository import (
    SqlAlchemyCategoriaRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_detalle_solicitud_repository import (
    SqlAlchemyDetalleSolicitudRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_historial_precio_repository import (
    SqlAlchemyHistorialPrecioRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_movimiento_inventario_repository import (
    SqlAlchemyMovimientoInventarioRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_pago_proveedor_repository import (
    SqlAlchemyPagoProveedorRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_producto_repository import (
    SqlAlchemyProductoRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_proveedor_repository import (
    SqlAlchemyProveedorRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_solicitud_ingreso_repository import (
    SqlAlchemySolicitudIngresoRepository,
)
from app.modules.modulo_b_inventario.infrastructure.adapters.storage.drive_storage_adapter import (
    DriveStorageAdapter,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.database.sqlalchemy_oauth_token_repository import (
    SqlAlchemyOAuthTokenRepository,
)
from app.modules.modulo_d_documentos.infrastructure.adapters.external.google_drive_adapter import (
    GoogleDriveAdapter,
)


def _storage(db: AsyncSession) -> DriveStorageAdapter:
    """Las boletas van al Drive del negocio, el mismo de los respaldos.

    No puede ser singleton como el adaptador de Supabase: Drive necesita el
    token OAuth, que vive en la BD y se lee con la sesión del request.
    """
    return DriveStorageAdapter(
        GoogleDriveAdapter(token_repository=SqlAlchemyOAuthTokenRepository(db))
    )


# =============================================================================
# Repositorios (factory functions)
# =============================================================================


def producto_repository(db: AsyncSession) -> SqlAlchemyProductoRepository:
    return SqlAlchemyProductoRepository(db)


def categoria_repository(db: AsyncSession) -> SqlAlchemyCategoriaRepository:
    return SqlAlchemyCategoriaRepository(db)


def solicitud_ingreso_repository(
    db: AsyncSession,
) -> SqlAlchemySolicitudIngresoRepository:
    return SqlAlchemySolicitudIngresoRepository(db)


def detalle_solicitud_repository(
    db: AsyncSession,
) -> SqlAlchemyDetalleSolicitudRepository:
    return SqlAlchemyDetalleSolicitudRepository(db)


def proveedor_repository(db: AsyncSession) -> SqlAlchemyProveedorRepository:
    return SqlAlchemyProveedorRepository(db)


def pago_proveedor_repository(db: AsyncSession) -> SqlAlchemyPagoProveedorRepository:
    return SqlAlchemyPagoProveedorRepository(db)


def movimiento_inventario_repository(
    db: AsyncSession,
) -> SqlAlchemyMovimientoInventarioRepository:
    return SqlAlchemyMovimientoInventarioRepository(db)


def historial_precio_repository(
    db: AsyncSession,
) -> SqlAlchemyHistorialPrecioRepository:
    return SqlAlchemyHistorialPrecioRepository(db)


# =============================================================================
# Use cases (factorías)
# =============================================================================


def crear_producto_usecase(db: AsyncSession) -> CrearProductoUseCase:
    return CrearProductoUseCase(
        producto_repository(db),
        categoria_repository(db),
        historial_precio_repository(db),
        contenedor_a.auditoria_usecase(db),
    )


def editar_producto_usecase(db: AsyncSession) -> EditarProductoUseCase:
    return EditarProductoUseCase(
        producto_repository(db), contenedor_a.auditoria_usecase(db)
    )


def ajustar_stock_usecase(db: AsyncSession) -> AjustarStockUseCase:
    return AjustarStockUseCase(
        producto_repository(db),
        movimiento_inventario_repository(db),
        contenedor_a.auditoria_usecase(db),
        contenedor_d.notificador(db),
    )


def eliminar_producto_usecase(db: AsyncSession) -> EliminarProductoUseCase:
    return EliminarProductoUseCase(
        producto_repository(db), contenedor_a.auditoria_usecase(db)
    )


def actualizar_producto_usecase(db: AsyncSession) -> ActualizarProductoUseCase:
    # Compat con router existente
    return ActualizarProductoUseCase(producto_repository(db))


def buscar_producto_por_codigo_usecase(
    db: AsyncSession,
) -> BuscarProductoPorCodigoUseCase:
    return BuscarProductoPorCodigoUseCase(producto_repository(db))


def buscar_producto_por_nombre_usecase(
    db: AsyncSession,
) -> BuscarProductoPorNombreUseCase:
    return BuscarProductoPorNombreUseCase(producto_repository(db))


def listar_productos_usecase(db: AsyncSession) -> ListarProductosUseCase:
    return ListarProductosUseCase(producto_repository(db))


def listar_productos_por_reponer_usecase(
    db: AsyncSession,
) -> ListarProductosPorReponerUseCase:
    return ListarProductosPorReponerUseCase(producto_repository(db))


def cambiar_precio_usecase(db: AsyncSession) -> CambiarPrecioUseCase:
    return CambiarPrecioUseCase(
        producto_repository(db),
        historial_precio_repository(db),
        contenedor_a.auditoria_usecase(db),
    )


def listar_historial_precios_usecase(
    db: AsyncSession,
) -> ListarHistorialPreciosUseCase:
    return ListarHistorialPreciosUseCase(historial_precio_repository(db))


def crear_categoria_usecase(db: AsyncSession) -> CrearCategoriaUseCase:
    return CrearCategoriaUseCase(
        categoria_repository(db), contenedor_a.auditoria_usecase(db)
    )


def editar_categoria_usecase(db: AsyncSession) -> EditarCategoriaUseCase:
    return EditarCategoriaUseCase(
        categoria_repository(db), contenedor_a.auditoria_usecase(db)
    )


def registrar_ingreso_usecase(db: AsyncSession) -> RegistrarIngresoUseCase:
    return RegistrarIngresoUseCase(
        solicitud_ingreso_repository(db),
        detalle_solicitud_repository(db),
        producto_repository(db),
        proveedor_repository(db),
        contenedor_a.auditoria_usecase(db),
        contenedor_d.notificador(db),
    )


def aprobar_ingreso_usecase(db: AsyncSession) -> AprobarIngresoUseCase:
    return AprobarIngresoUseCase(
        solicitud_ingreso_repository(db),
        detalle_solicitud_repository(db),
        producto_repository(db),
        movimiento_inventario_repository(db),
        contenedor_a.auditoria_usecase(db),
        # HU-B14: permite cargar la compra a crédito en la misma transacción.
        registrar_compra_credito_usecase(db),
    )


def rechazar_ingreso_usecase(db: AsyncSession) -> RechazarIngresoUseCase:
    return RechazarIngresoUseCase(
        solicitud_ingreso_repository(db), contenedor_a.auditoria_usecase(db)
    )


# sdd/modulo-b-aprobaciones-detalle-editar
def editar_ingreso_usecase(db: AsyncSession) -> EditarIngresoUseCase:
    return EditarIngresoUseCase(
        solicitud_ingreso_repository(db),
        detalle_solicitud_repository(db),
        contenedor_a.auditoria_usecase(db),
        producto_repository(db),
        proveedor_repository(db),
    )


def listar_ingresos_usecase(db: AsyncSession) -> ListarIngresosUseCase:
    return ListarIngresosUseCase(
        solicitud_ingreso_repository(db), detalle_solicitud_repository(db)
    )


def crear_proveedor_usecase(db: AsyncSession) -> CrearProveedorUseCase:
    return CrearProveedorUseCase(
        proveedor_repository(db), contenedor_a.auditoria_usecase(db)
    )


def editar_proveedor_usecase(db: AsyncSession) -> EditarProveedorUseCase:
    return EditarProveedorUseCase(
        proveedor_repository(db), contenedor_a.auditoria_usecase(db)
    )


def listar_proveedores_usecase(db: AsyncSession) -> ListarProveedoresUseCase:
    return ListarProveedoresUseCase(proveedor_repository(db))


def registrar_compra_credito_usecase(
    db: AsyncSession,
) -> RegistrarCompraCreditoUseCase:
    return RegistrarCompraCreditoUseCase(
        proveedor_repository(db),
        pago_proveedor_repository(db),
        solicitud_ingreso_repository(db),
        contenedor_a.auditoria_usecase(db),
    )


def registrar_pago_proveedor_usecase(
    db: AsyncSession,
) -> RegistrarPagoProveedorUseCase:
    return RegistrarPagoProveedorUseCase(
        proveedor_repository(db),
        pago_proveedor_repository(db),
        contenedor_a.auditoria_usecase(db),
    )


def listar_pagos_proveedor_usecase(
    db: AsyncSession,
) -> ListarPagosProveedorUseCase:
    return ListarPagosProveedorUseCase(
        pago_proveedor_repository(db), proveedor_repository(db)
    )


def listar_movimientos_inventario_usecase(
    db: AsyncSession,
) -> ListarMovimientosInventarioUseCase:
    return ListarMovimientosInventarioUseCase(movimiento_inventario_repository(db))


def subir_archivo_usecase(db: AsyncSession) -> SubirArchivoUseCase:
    return SubirArchivoUseCase(_storage(db), contenedor_a.auditoria_usecase(db))


async def refirmar_archivo(db: AsyncSession, carpeta: str, path: str):
    """Devuelve la URL de un archivo ya subido a partir de su id de Drive.

    Con Supabase la URL firmada vencía y había que regenerarla (HU-B07); el
    enlace de Drive es permanente, así que esto sólo la recompone.
    """
    return await _storage(db).refirmar(carpeta, path)
