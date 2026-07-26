# Router HTTP: /ingresos/* — flujo de aprobación en 2 pasos (D-09).
from datetime import date as date_type
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_current_user,
    get_auditoria,
    require_permission,
)
from app.modules.modulo_b_inventario import module_container as contenedor
from app.modules.modulo_b_inventario.application.registrar_ingreso_usecase import (
    LineaSolicitudDTO,
)
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    AprobarIngresoRequest,
    AprobacionResponse,
    DetalleCreate,
    IngresosPaginadosResponse,
    RechazarIngresoRequest,
    SolicitudIngresoCreate,
    SolicitudIngresoResponse,
    SolicitudIngresoUpdateRequest,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/ingresos", tags=["Inventario - Ingresos"])


@router.post("", response_model=SolicitudIngresoResponse, status_code=201)
async def crear(
    datos: SolicitudIngresoCreate,
    request: Request,
    usuario: Usuario = Depends(require_permission("inventario.solicitar_ingreso")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    lineas = [
        LineaSolicitudDTO(
            producto_id=l.producto_id,
            cantidad=l.cantidad,
            precio_compra_unitario=Decimal(str(l.precio_compra_unitario)),
        )
        for l in datos.lineas
    ]
    creada = await contenedor.registrar_ingreso_usecase(db).ejecutar(
        proveedor_id=datos.proveedor_id,
        foto_boleta_url=datos.foto_boleta_url,
        lineas=lineas,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return SolicitudIngresoResponse.desde_entidad(creada)


@router.get("", response_model=IngresosPaginadosResponse)
async def listar(
    estado: str | None = None,
    proveedor_id: int | None = None,
    fecha_desde: date_type | None = None,
    fecha_hasta: date_type | None = None,
    page: int = 1,
    page_size: int = 20,
    usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    resultado, total, page, page_size, total_pages = await contenedor.listar_ingresos_usecase(
        db
    ).ejecutar(
        estado=estado,
        proveedor_id=proveedor_id,
        fecha_desde=fecha_desde.isoformat() if fecha_desde else None,
        fecha_hasta=fecha_hasta.isoformat() if fecha_hasta else None,
        page=page,
        page_size=page_size,
        usuario=usuario,
    )
    items = [
        SolicitudIngresoResponse.desde_entidad(
            r["solicitud"],
            cantidad_productos=r["cantidad_productos"],
            monto_total=r["monto_total"],
        )
        for r in resultado
    ]
    return IngresosPaginadosResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get("/{solicitud_id}", response_model=SolicitudIngresoResponse)
async def obtener(
    solicitud_id: int,
    usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_solicitud_ingreso_repository import (
        SqlAlchemySolicitudIngresoRepository,
    )

    repo = SqlAlchemySolicitudIngresoRepository(db)
    s = await repo.find_by_id(solicitud_id)
    if s is None:
        from app.shared.kernel.exceptions import NoEncontradoError
        raise NoEncontradoError("Solicitud no encontrada.")
    # Defensa en profundidad: CAJERO solo ve lo propio
    if usuario.rol_nombre == "CAJERO" and s.solicitado_por != usuario.id:
        from app.shared.kernel.exceptions import ProhibidoError
        raise ProhibidoError("No tiene permisos para ver esta solicitud.")
    from decimal import Decimal
    cantidad = sum(l.cantidad for l in s.lineas)
    monto = sum(
        (l.cantidad * l.precio_compra_unitario for l in s.lineas),
        start=Decimal("0"),
    )
    return SolicitudIngresoResponse.desde_entidad(
        s, cantidad_productos=cantidad, monto_total=float(monto)
    )


@router.post("/{solicitud_id}/aprobar", response_model=AprobacionResponse)
async def aprobar(
    solicitud_id: int,
    body: AprobarIngresoRequest | None = None,
    request: Request = None,  # type: ignore[assignment]
    usuario: Usuario = Depends(require_permission("inventario.aprobar_ingreso")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    resultado = await contenedor.aprobar_ingreso_usecase(db).ejecutar(
        solicitud_id=solicitud_id,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        registrar_credito=bool(body and body.registrar_credito),
        ip=ip,
        user_agent=user_agent,
    )
    return AprobacionResponse(
        id=resultado.solicitud.id,  # type: ignore[arg-type]
        estado=str(resultado.solicitud.estado),
        revisado_por_nombre=resultado.solicitud.revisado_por_nombre or "",
        revisado_en=resultado.solicitud.revisado_en,
        productos_actualizados=resultado.productos_actualizados,
        unidades_agregadas=resultado.unidades_agregadas,
        monto_total=float(resultado.monto_total),
        credito_registrado=resultado.credito_registrado,
    )


@router.post("/{solicitud_id}/rechazar", response_model=SolicitudIngresoResponse)
async def rechazar(
    solicitud_id: int,
    datos: RechazarIngresoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("inventario.aprobar_ingreso")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    rechazada = await contenedor.rechazar_ingreso_usecase(db).ejecutar(
        solicitud_id=solicitud_id,
        motivo=datos.motivo_rechazo,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return SolicitudIngresoResponse.desde_entidad(rechazada)


# sdd/modulo-b-aprobaciones-detalle-editar
@router.patch(
    "/{solicitud_id}",
    response_model=SolicitudIngresoResponse,
    responses={
        403: {"description": "Sin permiso para editar"},
        404: {"description": "Solicitud no existe o fue eliminada"},
        409: {"description": "La solicitud ya no se puede editar (cambió de estado)"},
        422: {"description": "Body inválido (allowlist, motivo, cantidad)"},
    },
    summary="Edita una solicitud de ingreso en estado Pendiente (FR-3)",
)
async def editar(
    solicitud_id: int,
    body: SolicitudIngresoUpdateRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("inventario.solicitar_ingreso")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    from decimal import Decimal as _Dec

    ip, user_agent = contexto_request(request)
    es_admin = usuario.rol_nombre == "ADMIN"

    # Pydantic v2 ya parsea y valida el body. Acá pasamos los kwargs al use case
    # con `...` (Ellipsis) como sentinel para "no presente".
    # `body.valor(campo)` devuelve `...` cuando el campo NO vino en el body: sin
    # esto, un PATCH de solo `lineas` mandaba `proveedor_id=None` y BORRABA el
    # proveedor de la solicitud.
    resultado = await contenedor.editar_ingreso_usecase(db).ejecutar(
        ingreso_id=solicitud_id,
        editor_id=usuario.id,  # type: ignore[union-attr]
        editor_nombre=usuario.nombre,
        es_admin=es_admin,
        motivo=body.valor("motivo"),
        foto_boleta_url=...,  # no expuesto en esta versión (decisión §10)
        proveedor_id=body.valor("proveedor_id"),
        lineas=(
            [
                {
                    "producto_id": l.producto_id,
                    "cantidad": l.cantidad,
                    "precio_unitario": _Dec(str(l.precio_unitario)),
                }
                for l in body.lineas
            ]
            if body.lineas is not None
            else ...  # ausente o null: no se tocan las líneas ([] sí las vacía)
        ),
        ip=ip,
        user_agent=user_agent,
    )
    # Recalcular monto_total y cantidad_productos server-side
    cantidad = sum(l.cantidad for l in resultado.lineas)
    monto = sum(
        (l.cantidad * l.precio_compra_unitario for l in resultado.lineas),
        start=_Dec("0"),
    )
    return SolicitudIngresoResponse.desde_entidad(
        resultado, cantidad_productos=cantidad, monto_total=float(monto)
    )
