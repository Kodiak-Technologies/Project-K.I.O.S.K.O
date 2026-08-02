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
    VentasPaginadasResponse,
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
        client_uuid=datos.client_uuid,
        registrada_offline=datos.registrada_offline,
        vendida_en=datos.vendida_en,
        ip=ip,
        user_agent=user_agent,
    )
    return VentaResponse.desde_entidad(venta)


@router.get("", response_model=VentasPaginadasResponse)
async def listar(
    desde: date | None = None,
    hasta: date | None = None,
    turno_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Historial paginado. Antes devolvía TODAS las ventas del rango: el
    histórico crece sin techo y la pantalla las acumulaba sin límite."""
    ventas, total = await contenedor.consultar_ventas_usecase(db).listar(
        desde, hasta, turno_id, page, page_size
    )
    return VentasPaginadasResponse(
        items=[VentaResponse.desde_entidad(v) for v in ventas],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/{venta_id}", response_model=VentaResponse)
async def obtener(
    venta_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Una venta con sus items y pagos. Evita tener que recorrer el listado
    completo para encontrarla (lo que hacía el Módulo D)."""
    venta = await contenedor.consultar_ventas_usecase(db).obtener(venta_id)
    return VentaResponse.desde_entidad(venta)


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
    await contenedor.anular_venta_usecase(db).anular(
        venta_id=venta_id,
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        motivo=datos.motivo,
        ip=ip,
        user_agent=user_agent,
    )
    venta = await contenedor.consultar_ventas_usecase(db).obtener(venta_id)
    return VentaResponse.desde_entidad(venta)


@router.post("/{venta_id}/devolver", response_model=VentaResponse)
async def devolver(
    datos: DevolverVentaRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("ventas.devolver")),
    db: AsyncSession = Depends(get_db),
    venta_id: int = 0,
):
    # Devolución parcial (cambio de producto): repone solo lo devuelto.
    ip, user_agent = contexto_request(request)
    await contenedor.anular_venta_usecase(db).devolver(
        venta_id=venta_id,
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        items=[(i.detalle_id, i.cantidad) for i in datos.items],
        motivo=datos.motivo,
        ip=ip,
        user_agent=user_agent,
    )
    venta = await contenedor.consultar_ventas_usecase(db).obtener(venta_id)
    return VentaResponse.desde_entidad(venta)
