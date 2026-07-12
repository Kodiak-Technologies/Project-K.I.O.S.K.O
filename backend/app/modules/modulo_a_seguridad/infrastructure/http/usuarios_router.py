# Router HTTP: /usuarios/* (todo protegido con el permiso usuarios.gestionar — solo ADMIN).
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_usuario_repository import (
    SqlAlchemyUsuarioRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    require_permission,
)
from app.modules.modulo_a_seguridad.infrastructure.http.schemas import (
    CambiarEstadoRequest,
    CrearUsuarioRequest,
    EditarUsuarioRequest,
    EliminarUsuarioRequest,
    ResetearPasswordRequest,
    UsuarioResponse,
)
from app.shared.database.session import get_db
from app.shared.kernel.exceptions import NoEncontradoError

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

_solo_gestion_usuarios = require_permission("usuarios.gestionar")


@router.get("", response_model=list[UsuarioResponse])
async def listar(
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    usuarios = await SqlAlchemyUsuarioRepository(db).listar()
    return [UsuarioResponse.desde_entidad(u) for u in usuarios]


@router.post("", response_model=UsuarioResponse, status_code=201)
async def crear(
    datos: CrearUsuarioRequest,
    request: Request,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    creado = await contenedor.crear_usuario_usecase(db).ejecutar(
        admin, datos.username, datos.nombre, datos.password, datos.rol_id,
        datos.forzar_cambio_password, ip, user_agent,
    )
    return UsuarioResponse.desde_entidad(creado)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def obtener(
    usuario_id: int,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    usuario = await SqlAlchemyUsuarioRepository(db).buscar_por_id(usuario_id)
    if usuario is None or usuario.eliminado:
        raise NoEncontradoError("Usuario no encontrado.")
    return UsuarioResponse.desde_entidad(usuario)


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
async def editar(
    usuario_id: int,
    datos: EditarUsuarioRequest,
    request: Request,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    actualizado = await contenedor.editar_usuario_usecase(db).ejecutar(
        admin, usuario_id, datos.nombre, datos.rol_id, ip, user_agent
    )
    return UsuarioResponse.desde_entidad(actualizado)


@router.delete("/{usuario_id}", status_code=204)
async def eliminar(
    usuario_id: int,
    request: Request,
    datos: EliminarUsuarioRequest | None = None,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    # Borrado LÓGICO: el registro y su historial permanecen (nada se elimina físicamente).
    ip, user_agent = contexto_request(request)
    motivo = datos.motivo if datos else None
    await contenedor.eliminar_usuario_usecase(db).ejecutar(admin, usuario_id, motivo, ip, user_agent)


@router.patch("/{usuario_id}/estado", response_model=UsuarioResponse)
async def cambiar_estado(
    usuario_id: int,
    datos: CambiarEstadoRequest,
    request: Request,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    actualizado = await contenedor.cambiar_estado_usuario_usecase(db).ejecutar(
        admin, usuario_id, datos.activo, ip, user_agent
    )
    return UsuarioResponse.desde_entidad(actualizado)


@router.patch("/{usuario_id}/password", status_code=204)
async def resetear_password(
    usuario_id: int,
    datos: ResetearPasswordRequest,
    request: Request,
    admin: Usuario = Depends(_solo_gestion_usuarios),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    await contenedor.resetear_password_usecase(db).ejecutar(
        admin, usuario_id, datos.password_nueva, datos.forzar_cambio, ip, user_agent
    )
