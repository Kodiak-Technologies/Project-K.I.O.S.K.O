# Router HTTP: /mermas/* — flujo de validación 2 pasos (D-14).
from datetime import date as date_type
from decimal import Decimal

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
    MermaConfirmarResponse,
    MermaCreate,
    MermaResponse,
    MermasPaginadosResponse,
    RechazarMermaRequest,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/mermas", tags=["Inventario - Mermas"])


@router.post("", response_model=MermaResponse, status_code=201)
async def crear(
    datos: MermaCreate,
    request: Request,
    usuario: Usuario = Depends(require_permission("mermas.registrar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    creada = await contenedor.registrar_merma_usecase(db).ejecutar(
        producto_id=datos.producto_id,
        cantidad=datos.cantidad,
        motivo=datos.motivo,
        observacion=datos.observacion,
        proveedor_id=datos.proveedor_id,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return MermaResponse.desde_entidad(creada)


@router.get("", response_model=MermasPaginadosResponse)
async def listar(
    estado: str | None = None,
    motivo: str | None = None,
    producto_id: int | None = None,
    fecha_desde: date_type | None = None,
    fecha_hasta: date_type | None = None,
    page: int = 1,
    page_size: int = 20,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    items, total, page, page_size, total_pages = await contenedor.listar_mermas_usecase(
        db
    ).ejecutar(
        estado=estado,
        motivo=motivo,
        producto_id=producto_id,
        fecha_desde=fecha_desde.isoformat() if fecha_desde else None,
        fecha_hasta=fecha_hasta.isoformat() if fecha_hasta else None,
        page=page,
        page_size=page_size,
    )
    return MermasPaginadosResponse(
        items=[MermaResponse.desde_entidad(m) for m in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.get("/{merma_id}", response_model=MermaResponse)
async def obtener(
    merma_id: int,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_merma_repository import (
        SqlAlchemyMermaRepository,
    )

    repo = SqlAlchemyMermaRepository(db)
    m = await repo.find_by_id(merma_id)
    if m is None:
        from app.shared.kernel.exceptions import NoEncontradoError
        raise NoEncontradoError("Merma no encontrada.")
    return MermaResponse.desde_entidad(m)


@router.post("/{merma_id}/confirmar", response_model=MermaConfirmarResponse)
async def confirmar(
    merma_id: int,
    request: Request,
    usuario: Usuario = Depends(require_permission("mermas.confirmar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    resultado = await contenedor.confirmar_merma_usecase(db).ejecutar(
        merma_id=merma_id,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return MermaConfirmarResponse(
        id=resultado.merma.id,  # type: ignore[arg-type]
        estado=str(resultado.merma.estado),
        confirmado_por_nombre=resultado.merma.confirmado_por_nombre or "",
        confirmado_en=resultado.merma.confirmado_en,
        stock_actualizado=resultado.stock_actualizado,
    )


@router.post("/{merma_id}/rechazar", response_model=MermaResponse)
async def rechazar(
    merma_id: int,
    datos: RechazarMermaRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("mermas.confirmar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    rechazada = await contenedor.rechazar_merma_usecase(db).ejecutar(
        merma_id=merma_id,
        motivo=datos.motivo_rechazo,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return MermaResponse.desde_entidad(rechazada)
