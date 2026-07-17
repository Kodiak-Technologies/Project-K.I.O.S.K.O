# Router HTTP: /ventas/*. Sin lógica de negocio.
from datetime import date

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
    RegistrarVentaRequest,
    VentaResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/ventas", tags=["Ventas"])


@router.post("", response_model=VentaResponse, status_code=201)
async def registrar(
    datos: RegistrarVentaRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("ventas.registrar")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    venta = await contenedor.registrar_venta_usecase(db).ejecutar(
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        items=[(i.producto_id, i.cantidad) for i in datos.items],
        pagos=datos.pagos_normalizados(),
        ip=ip,
        user_agent=user_agent,
    )
    return VentaResponse.desde_entidad(venta)


@router.get("", response_model=list[VentaResponse])
async def listar(
    desde: date | None = None,
    hasta: date | None = None,
    turno_id: int | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ventas = await contenedor.consultar_ventas_usecase(db).listar(desde, hasta, turno_id)
    return [VentaResponse.desde_entidad(v) for v in ventas]
