# Router HTTP: /categorias/*. Sin lógica de negocio.
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    get_current_user,
    require_permission,
)
from app.modules.modulo_b_inventario import module_container as contenedor
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    CategoriaResponse,
    CrearCategoriaRequest,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/categorias", tags=["Inventario"])


@router.get("", response_model=list[CategoriaResponse])
async def listar(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    categorias = await contenedor.categoria_repository(db).listar()
    return [CategoriaResponse.desde_entidad(c) for c in categorias]


@router.post("", response_model=CategoriaResponse, status_code=201)
async def crear(
    datos: CrearCategoriaRequest,
    usuario: Usuario = Depends(require_permission("productos.crear")),
    db: AsyncSession = Depends(get_db),
):
    creada = await contenedor.categoria_repository(db).crear(datos.nombre)
    return CategoriaResponse.desde_entidad(creada)
