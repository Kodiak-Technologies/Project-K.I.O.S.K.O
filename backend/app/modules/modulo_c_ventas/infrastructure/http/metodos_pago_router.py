# Router HTTP: /metodos-pago/*. Catálogo de métodos de pago (RF-20).
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_current_user,
    require_permission,
)
from app.modules.modulo_c_ventas import module_container as contenedor
from app.modules.modulo_c_ventas.infrastructure.http.schemas import (
    ActualizarMetodoPagoRequest,
    CrearMetodoPagoRequest,
    MetodoPagoResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/metodos-pago", tags=["Ventas"])


@router.get("", response_model=list[MetodoPagoResponse])
async def listar(
    todos: bool = False,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # `todos=true` incluye los desactivados (para la pantalla de gestión del ADMIN).
    metodos = await contenedor.gestionar_metodos_pago_usecase(db).listar(solo_activos=not todos)
    return [MetodoPagoResponse.desde_entidad(m) for m in metodos]


@router.post("", response_model=MetodoPagoResponse, status_code=201)
async def crear(
    datos: CrearMetodoPagoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("metodos_pago.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    creado = await contenedor.gestionar_metodos_pago_usecase(db).crear(
        admin_id=usuario.id, rol=usuario.rol_nombre,
        codigo=datos.codigo, nombre=datos.nombre, es_efectivo=datos.es_efectivo,
        ip=ip, user_agent=user_agent,
    )
    return MetodoPagoResponse.desde_entidad(creado)


@router.patch("/{metodo_id}", response_model=MetodoPagoResponse)
async def actualizar(
    metodo_id: int,
    datos: ActualizarMetodoPagoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("metodos_pago.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    actualizado = await contenedor.gestionar_metodos_pago_usecase(db).actualizar(
        admin_id=usuario.id, rol=usuario.rol_nombre,
        metodo_id=metodo_id, cambios=datos.model_dump(exclude_unset=True),
        ip=ip, user_agent=user_agent,
    )
    return MetodoPagoResponse.desde_entidad(actualizado)
