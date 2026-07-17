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
    AnularVentaRequest,
    DevolverVentaRequest,
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
        cliente_id=datos.cliente_id,
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


@router.post("/{venta_id}/anular", response_model=VentaResponse)
async def anular(
    venta_id: int,
    datos: AnularVentaRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("ventas.anular")),
    db: AsyncSession = Depends(get_db),
):
    # La venta no se borra: reverso total que repone stock y ajusta la caja
    # del turno actual, con rastro para la administradora (RF-22).
    ip, user_agent = contexto_request(request)
    venta = await contenedor.anular_venta_usecase(db).anular(
        venta_id=venta_id,
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        motivo=datos.motivo,
        ip=ip,
        user_agent=user_agent,
    )
    return VentaResponse.desde_entidad(venta)


@router.post("/{venta_id}/devolver", response_model=VentaResponse)
async def devolver(
    venta_id: int,
    datos: DevolverVentaRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("ventas.devolver")),
    db: AsyncSession = Depends(get_db),
):
    # Devolución parcial (cambio de producto): repone solo lo devuelto.
    ip, user_agent = contexto_request(request)
    venta = await contenedor.anular_venta_usecase(db).devolver(
        venta_id=venta_id,
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        items=[(i.detalle_id, i.cantidad) for i in datos.items],
        motivo=datos.motivo,
        ip=ip,
        user_agent=user_agent,
    )
    return VentaResponse.desde_entidad(venta)
