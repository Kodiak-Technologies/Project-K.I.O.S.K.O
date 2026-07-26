# Router HTTP: /productos/*. Sin lógica de negocio.
# EXTENDIDO en PR2: GET /buscar, GET /{id}, GET /por-reponer, PATCH /{id},
# PATCH /{id}/precio, GET /{id}/historial-precios.
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_auditoria,
    get_current_user,
    require_permission,
)
from app.modules.modulo_b_inventario import module_container as contenedor
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    ActualizarProductoRequest,
    CambiarPrecioRequest,
    CambiarPrecioResponse,
    CrearProductoRequest,
    HistorialPaginadosResponse,
    HistorialPrecioResponse,
    MarcarAlertasRequest,
    MarcarAlertasResponse,
    PorReponerItemResponse,
    PorReponerPaginadosResponse,
    ProductoResponse,
    ProductosPaginadosResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/productos", tags=["Inventario"])


# =============================================================================
# Catálogo: alta, edición, listado, búsqueda
# =============================================================================


@router.get("", response_model=ProductosPaginadosResponse)
async def listar(
    search: str | None = None,
    categoria_id: int | None = None,
    solo_con_stock: bool = False,
    solo_bajo_minimo: bool = False,
    activo: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    items, total, page, page_size, total_pages = await contenedor.listar_productos_usecase(
        db
    ).ejecutar(
        search=search,
        categoria_id=categoria_id,
        solo_con_stock=solo_con_stock,
        solo_bajo_minimo=solo_bajo_minimo,
        activo=activo,
        page=page,
        page_size=page_size,
    )
    return ProductosPaginadosResponse(
        items=[ProductoResponse.desde_entidad(p) for p in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.get("/buscar", response_model=ProductoResponse | list[ProductoResponse])
async def buscar(
    codigo: str | None = None,
    nombre: str | None = None,
    categoria_id: int | None = None,
    limit: int = 20,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    if codigo:
        p = await contenedor.buscar_producto_por_codigo_usecase(db).ejecutar(codigo)
        return ProductoResponse.desde_entidad(p)
    if nombre:
        items = await contenedor.buscar_producto_por_nombre_usecase(db).ejecutar(
            nombre=nombre, categoria_id=categoria_id, limit=limit
        )
        return [ProductoResponse.desde_entidad(p) for p in items]
    from app.shared.kernel.exceptions import ValidacionError
    raise ValidacionError("Debes enviar ?codigo= o ?nombre=.")


@router.get("/por-reponer", response_model=PorReponerPaginadosResponse)
async def listar_por_reponer(
    categoria_id: int | None = None,
    solo_no_notificadas: bool = False,
    page: int = 1,
    page_size: int = 20,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    """HU-B13. Con `solo_no_notificadas=true` devuelve únicamente los productos
    cuya alerta todavía no se avisó (alerta única hasta la reposición)."""
    items, total, page, page_size, total_pages = await contenedor.listar_productos_por_reponer_usecase(
        db
    ).ejecutar(
        categoria_id=categoria_id,
        solo_no_notificadas=solo_no_notificadas,
        page=page,
        page_size=page_size,
    )
    return PorReponerPaginadosResponse(
        items=[PorReponerItemResponse.desde_item(i) for i in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/por-reponer/marcar-notificadas", response_model=MarcarAlertasResponse)
async def marcar_alertas_notificadas(
    datos: MarcarAlertasRequest,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    """HU-B13: marca las alertas ya mostradas. Se rearman solas cuando el
    producto se repone por encima de su stock mínimo."""
    marcados = await contenedor.listar_productos_por_reponer_usecase(
        db
    ).marcar_notificadas(datos.producto_ids)
    return MarcarAlertasResponse(marcados=marcados)


@router.get("/{producto_id}", response_model=ProductoResponse)
async def obtener(
    producto_id: int,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    from app.shared.kernel.exceptions import NoEncontradoError
    repo = contenedor.producto_repository(db)
    p = await repo.buscar_por_id(producto_id)
    if p is None or p.deleted_at is not None:
        raise NoEncontradoError("Producto no encontrado.")
    return ProductoResponse.desde_entidad(p)


@router.post("", response_model=ProductoResponse, status_code=201)
async def crear(
    datos: CrearProductoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("productos.crear")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    creado = await contenedor.crear_producto_usecase(db).ejecutar(
        codigo=datos.codigo,
        nombre=datos.nombre,
        categoria_id=datos.categoria_id,
        precio_venta=Decimal(str(datos.precio_venta)),
        precio_compra_actual=Decimal(str(datos.precio_compra_actual)),
        stock_minimo=datos.stock_minimo,
        stock_inicial=datos.stock_inicial,
        es_codigo_interno=datos.es_codigo_interno,
        foto_url=datos.foto_url,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return ProductoResponse.desde_entidad(creado)


@router.patch("/{producto_id}", response_model=ProductoResponse)
async def editar(
    producto_id: int,
    datos: ActualizarProductoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("productos.editar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    # `ProductoUpdate` tiene extra="forbid": mandar precio/precio_compra_actual
    # ya devuelve 422 en la validación del body (antes se ignoraba en silencio).
    cambios = datos.model_dump(exclude_unset=True)
    ip, user_agent = contexto_request(request)
    actualizado = await contenedor.editar_producto_usecase(db).ejecutar(
        producto_id=producto_id,
        cambios=cambios,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return ProductoResponse.desde_entidad(actualizado)


# =============================================================================
# Cambio de precio (HU-B11)
# =============================================================================


@router.patch("/{producto_id}/precio", response_model=CambiarPrecioResponse)
async def cambiar_precio(
    producto_id: int,
    datos: CambiarPrecioRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("precios.editar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    producto, historial_registrado, filas = await contenedor.cambiar_precio_usecase(
        db
    ).ejecutar(
        producto_id=producto_id,
        precio_venta=Decimal(str(datos.precio_venta)) if datos.precio_venta is not None else None,
        precio_compra_actual=(
            Decimal(str(datos.precio_compra_actual))
            if datos.precio_compra_actual is not None
            else None
        ),
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return CambiarPrecioResponse.desde(producto, historial_registrado, filas)


# =============================================================================
# Historial de precios (HU-B11)
# =============================================================================


@router.get("/{producto_id}/historial-precios", response_model=HistorialPaginadosResponse)
async def historial_precios(
    producto_id: int,
    tipo: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _usuario: Usuario = Depends(require_permission("historial_precios.ver")),
    db: AsyncSession = Depends(get_db),
):
    items, total, page, page_size, total_pages = await contenedor.listar_historial_precios_usecase(
        db
    ).ejecutar(producto_id=producto_id, tipo=tipo, page=page, page_size=page_size)
    return HistorialPaginadosResponse(
        items=[HistorialPrecioResponse.desde_entidad(h) for h in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )
