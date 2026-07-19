# Router HTTP: /productos/*. Sin lógica de negocio.
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
    CrearProductoRequest,
    ProductoResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/productos", tags=["Inventario"])


@router.get("", response_model=list[ProductoResponse])
async def listar(
    q: str | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    productos = await contenedor.producto_repository(db).listar(q)
    return [ProductoResponse.desde_entidad(p) for p in productos]


@router.post("", response_model=ProductoResponse, status_code=201)
async def crear(
    datos: CrearProductoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("productos.crear")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    creado = await contenedor.crear_producto_usecase(db).ejecutar(
        codigo=datos.codigo,
        nombre=datos.nombre,
        categoria_id=datos.categoria_id,
        precio=Decimal(str(datos.precio)),
        stock_minimo=datos.stock_minimo,
        stock_inicial=datos.stock_inicial,
    )
    ip, user_agent = contexto_request(request)
    await auditoria.ejecutar(
        accion="producto_creado", entidad="productos", entidad_id=creado.id,
        usuario_id=usuario.id, rol=usuario.rol_nombre,
        valor_nuevo={"codigo": creado.codigo, "nombre": creado.nombre,
                     "precio": float(creado.precio), "stock": creado.stock},
        ip=ip, user_agent=user_agent,
    )
    return ProductoResponse.desde_entidad(creado)


@router.patch("/{producto_id}", response_model=ProductoResponse)
async def actualizar(
    producto_id: int,
    datos: ActualizarProductoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("productos.editar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    cambios = datos.model_dump(exclude_unset=True)
    if "precio" in cambios and cambios["precio"] is not None:
        cambios["precio"] = Decimal(str(cambios["precio"]))
    anterior = await contenedor.producto_repository(db).buscar_por_id(producto_id)
    actualizado = await contenedor.actualizar_producto_usecase(db).ejecutar(producto_id, cambios)
    ip, user_agent = contexto_request(request)
    await auditoria.ejecutar(
        accion="producto_editado", entidad="productos", entidad_id=producto_id,
        usuario_id=usuario.id, rol=usuario.rol_nombre,
        valor_anterior={"nombre": anterior.nombre, "precio": float(anterior.precio),
                        "activo": anterior.activo} if anterior else None,
        valor_nuevo={k: (float(v) if isinstance(v, Decimal) else v) for k, v in cambios.items()},
        ip=ip, user_agent=user_agent,
    )
    return ProductoResponse.desde_entidad(actualizado)
