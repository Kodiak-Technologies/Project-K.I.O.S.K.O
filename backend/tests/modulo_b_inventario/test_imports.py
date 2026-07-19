"""Tests de import del esqueleto del Módulo B (PR1).

Verifica que TODOS los módulos del esqueleto (entidades, value objects, puertos,
modelos SQLAlchemy, adaptadores stub y storage adapter) se importan sin errores
y que no hay ciclos de import.

PR1 solo cubre el esqueleto + DDL; la lógica de negocio y los routers llegan en PR2.
"""
from __future__ import annotations


# =============================================================================
# Domain layer (Python puro, sin SQLAlchemy/FastAPI)
# =============================================================================


def test_import_entities() -> None:
    from app.modules.modulo_b_inventario.domain.entities import (
        Categoria,
        DetalleSolicitud,
        HistorialPrecio,
        Merma,
        MovimientoInventario,
        PagoProveedor,
        Producto,
        Proveedor,
        SolicitudIngreso,
    )

    assert all(
        cls is not None
        for cls in (
            Producto,
            Categoria,
            SolicitudIngreso,
            DetalleSolicitud,
            Merma,
            Proveedor,
            PagoProveedor,
            MovimientoInventario,
            HistorialPrecio,
        )
    )


def test_import_value_objects() -> None:
    from app.modules.modulo_b_inventario.domain.value_objects import (
        CodigoInterno,
        EstadoMerma,
        EstadoSolicitud,
        MotivoMerma,
        StorageResult,
        TipoMovimiento,
        TipoPago,
        TipoPrecio,
    )

    assert all(
        cls is not None
        for cls in (
            EstadoSolicitud,
            EstadoMerma,
            MotivoMerma,
            TipoPago,
            TipoMovimiento,
            TipoPrecio,
            CodigoInterno,
            StorageResult,
        )
    )


def test_import_puertos() -> None:
    from app.modules.modulo_b_inventario.domain.ports.categoria_repository_port import (
        CategoriaRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.current_user_port import (
        CurrentUserPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
        DetalleSolicitudRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.historial_precio_repository_port import (
        HistorialPrecioRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
        MermaRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.movimiento_inventario_repository_port import (
        MovimientoInventarioRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.pago_proveedor_repository_port import (
        PagoProveedorRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
        ProductoRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
        ProveedorRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
        SolicitudIngresoRepositoryPort,
    )
    from app.modules.modulo_b_inventario.domain.ports.storage_port import StoragePort

    ports = (
        ProductoRepositoryPort,
        CategoriaRepositoryPort,
        SolicitudIngresoRepositoryPort,
        DetalleSolicitudRepositoryPort,
        MermaRepositoryPort,
        ProveedorRepositoryPort,
        PagoProveedorRepositoryPort,
        MovimientoInventarioRepositoryPort,
        HistorialPrecioRepositoryPort,
        StoragePort,
        CurrentUserPort,
    )
    assert all(p is not None for p in ports)


# =============================================================================
# Infrastructure layer
# =============================================================================


def test_import_modelos() -> None:
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.models import (
        CategoriaModel,
        DetalleSolicitudModel,
        HistorialPrecioModel,
        MermaModel,
        MovimientoInventarioModel,
        PagoProveedorModel,
        ProductoModel,
        ProveedorModel,
        SolicitudIngresoModel,
    )

    # Smoke: los nombres de tabla son los esperados
    assert SolicitudIngresoModel.__tablename__ == "solicitudes_ingreso"
    assert DetalleSolicitudModel.__tablename__ == "detalle_solicitud"
    assert MermaModel.__tablename__ == "mermas"
    assert ProveedorModel.__tablename__ == "proveedores"
    assert PagoProveedorModel.__tablename__ == "pagos_proveedor"
    assert MovimientoInventarioModel.__tablename__ == "movimientos_inventario"
    assert HistorialPrecioModel.__tablename__ == "historial_precios"
    # Los 2 extendidos
    assert ProductoModel.__tablename__ == "productos"
    assert CategoriaModel.__tablename__ == "categorias"


def test_import_adaptadores_stub() -> None:
    """Los 7 adaptadores nuevos + el de storage + el repositorio de categoría
    (extraído) deben importar sin errores.
    """
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_categoria_repository import (
        SqlAlchemyCategoriaRepository,
    )
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_detalle_solicitud_repository import (
        SqlAlchemyDetalleSolicitudRepository,
    )
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_historial_precio_repository import (
        SqlAlchemyHistorialPrecioRepository,
    )
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_merma_repository import (
        SqlAlchemyMermaRepository,
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
    from app.modules.modulo_b_inventario.infrastructure.adapters.storage.supabase_storage_adapter import (
        SupabaseStorageAdapter,
    )

    # El storage adapter no debe depender del SDK `supabase` en PR1
    assert SupabaseStorageAdapter is not None


def test_adaptadores_stub_levantan_not_implemented() -> None:
    """Los métodos stub de PR1 deben levantar `NotImplementedError('Implementado en PR2')`.

    Verifica con uno de cada tipo (entidad, movimiento, storage).
    """
    import pytest
    from sqlalchemy.ext.asyncio import AsyncSession

    # AsyncSession real no es necesario para invocar los stubs: basta con None.
    # Pero para que la firma de los constructores sea feliz, usamos None
    # (los constructores guardan el arg pero no lo usan).
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_historial_precio_repository import (
        SqlAlchemyHistorialPrecioRepository,
    )
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_movimiento_inventario_repository import (
        SqlAlchemyMovimientoInventarioRepository,
    )
    from app.modules.modulo_b_inventario.infrastructure.adapters.storage.supabase_storage_adapter import (
        SupabaseStorageAdapter,
    )

    # type: ignore[arg-type]: pasamos None solo para instanciar.
    hist = SqlAlchemyHistorialPrecioRepository(None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError, match="Implementado en PR2"):
        # Las anotaciones son opcionales en el stub
        import asyncio

        asyncio.run(hist.append(None))  # type: ignore[arg-type]

    mov = SqlAlchemyMovimientoInventarioRepository(None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError, match="Implementado en PR2"):
        import asyncio

        asyncio.run(mov.append(None))  # type: ignore[arg-type]

    storage = SupabaseStorageAdapter()
    with pytest.raises(NotImplementedError, match="Implementado en PR2"):
        import asyncio

        asyncio.run(storage.subir("boletas", "x.jpg", b"data", "image/jpeg"))


# =============================================================================
# Wiring y compat con el skeleton existente
# =============================================================================


def test_module_container_importa() -> None:
    """El module_container sigue importando tras la extracción de CategoriaRepository."""
    from app.modules.modulo_b_inventario import module_container

    assert hasattr(module_container, "crear_producto_usecase")
    assert hasattr(module_container, "actualizar_producto_usecase")
    assert hasattr(module_container, "producto_repository")
    assert hasattr(module_container, "categoria_repository")


def test_use_cases_existen_compat() -> None:
    """Los use cases existentes (skeleton) siguen importando — son requeridos por
    los routers actuales (productos_router, categorias_router)."""
    from app.modules.modulo_b_inventario.application.crear_producto_usecase import (
        CrearProductoUseCase,
    )
    from app.modules.modulo_b_inventario.application.actualizar_producto_usecase import (
        ActualizarProductoUseCase,
    )

    assert CrearProductoUseCase is not None
    assert ActualizarProductoUseCase is not None


def test_no_hay_ciclo_de_imports_al_cargar_routers() -> None:
    """Si los routers del módulo B se importan, no debe haber ciclos."""
    # Solo importamos; el ciclo se manifestaría como ImportError.
    from app.modules.modulo_b_inventario.infrastructure.http import (  # noqa: F401
        categorias_router,
        productos_router,
    )
    from app.modules.modulo_b_inventario.infrastructure.http import (  # noqa: F401
        ingresos_router,
        inventario_router,
    )


def test_value_objects_validan_pertenencia() -> None:
    """Smoke test de los VOs: el valor válido se acepta, el inválido levanta
    `ValidacionError`."""
    import pytest

    from app.modules.modulo_b_inventario.domain.value_objects import (
        CodigoInterno,
        EstadoMerma,
        EstadoSolicitud,
        MotivoMerma,
        TipoPago,
        TipoPrecio,
    )
    from app.shared.kernel.exceptions import ValidacionError

    # Válidos
    assert str(EstadoSolicitud("Pendiente")) == "Pendiente"
    assert str(EstadoMerma("Confirmada")) == "Confirmada"
    assert str(MotivoMerma("vencimiento")) == "vencimiento"
    assert str(TipoPago("compra_credito")) == "compra_credito"
    assert str(TipoPrecio("venta")) == "venta"
    assert str(CodigoInterno("PAP-001")) == "PAP-001"

    # Inválidos
    with pytest.raises(ValidacionError):
        EstadoSolicitud("invalido")
    with pytest.raises(ValidacionError):
        MotivoMerma("robo")
    with pytest.raises(ValidacionError):
        CodigoInterno("malformado")
