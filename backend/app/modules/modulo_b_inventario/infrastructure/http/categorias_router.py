# Router HTTP: /categorias/*. Sin lógica de negocio.
# EXTENDIDO en PR2: PATCH /{id}, ajuste de permisos (categorias.gestionar).
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_auditoria,
    require_permission,
)
from app.modules.modulo_b_inventario import module_container as contenedor
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    CategoriaCreate,
    CategoriaResponse,
    CategoriaUpdate,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/categorias", tags=["Inventario"])


@router.get("", response_model=list[CategoriaResponse])
async def listar(
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    categorias = await contenedor.categoria_repository(db).listar()
    return [CategoriaResponse.desde_entidad(c) for c in categorias]


@router.post("", response_model=CategoriaResponse, status_code=201)
async def crear(
    datos: CategoriaCreate,
    request: Request,
    usuario: Usuario = Depends(require_permission("categorias.gestionar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    creada = await contenedor.crear_categoria_usecase(db).ejecutar(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return CategoriaResponse.desde_entidad(creada)


@router.patch("/{categoria_id}", response_model=CategoriaResponse)
async def editar(
    categoria_id: int,
    datos: CategoriaUpdate,
    request: Request,
    usuario: Usuario = Depends(require_permission("categorias.gestionar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    cambios = datos.model_dump(exclude_unset=True)
    actualizada = await contenedor.editar_categoria_usecase(db).ejecutar(
        categoria_id=categoria_id,
        cambios=cambios,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return CategoriaResponse.desde_entidad(actualizada)
