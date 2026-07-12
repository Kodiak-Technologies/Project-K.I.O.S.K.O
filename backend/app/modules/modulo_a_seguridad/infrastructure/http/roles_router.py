# Router HTTP: /roles y /permisos. Lectura para ADMIN; PUT reasigna permisos de un rol
# (los permisos viven en BD, así que el cambio aplica sin redeploy).
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_permiso_repository import (
    SqlAlchemyPermisoRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    require_permission,
)
from app.modules.modulo_a_seguridad.infrastructure.http.schemas import (
    AsignarPermisosRequest,
    PermisoResponse,
    RolResponse,
)
from app.shared.database.session import get_db

router = APIRouter(tags=["Roles y permisos"])

_solo_gestion_usuarios = require_permission("usuarios.gestionar")


@router.get("/roles", response_model=list[RolResponse])
async def listar_roles(
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    return [RolResponse.desde_entidad(r) for r in await SqlAlchemyPermisoRepository(db).listar_roles()]


@router.get("/permisos", response_model=list[PermisoResponse])
async def listar_permisos(
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    return [
        PermisoResponse.desde_entidad(p)
        for p in await SqlAlchemyPermisoRepository(db).listar_permisos()
    ]


@router.get("/roles/{rol_id}/permisos", response_model=list[PermisoResponse])
async def permisos_de_rol(
    rol_id: int,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    return [
        PermisoResponse.desde_entidad(p)
        for p in await SqlAlchemyPermisoRepository(db).permisos_de_rol(rol_id)
    ]


@router.put("/roles/{rol_id}/permisos", response_model=list[PermisoResponse])
async def asignar_permisos(
    rol_id: int,
    datos: AsignarPermisosRequest,
    request: Request,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    nuevos = await contenedor.asignar_permisos_usecase(db).ejecutar(
        admin, rol_id, datos.permisos, ip, user_agent
    )
    return [PermisoResponse.desde_entidad(p) for p in nuevos]
