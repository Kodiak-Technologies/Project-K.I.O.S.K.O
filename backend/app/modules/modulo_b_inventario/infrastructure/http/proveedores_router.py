# Router HTTP: /proveedores/* — gestión de proveedores y deuda (HU-B14).
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
    PagoProveedorCreate,
    PagoProveedorResponse,
    PagosPaginadosResponse,
    ProveedorCreate,
    ProveedorResponse,
    ProveedorUpdate,
    ProveedoresPaginadosResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/proveedores", tags=["Inventario - Proveedores"])


@router.get("", response_model=ProveedoresPaginadosResponse)
async def listar(
    search: str | None = None,
    solo_con_deuda: bool = False,
    activo: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    _usuario: Usuario = Depends(require_permission("proveedores.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    items, total, page, page_size, total_pages = await contenedor.listar_proveedores_usecase(
        db
    ).ejecutar(
        search=search,
        solo_con_deuda=solo_con_deuda,
        activo=activo,
        page=page,
        page_size=page_size,
    )
    return ProveedoresPaginadosResponse(
        items=[ProveedorResponse.desde_entidad(p) for p in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("", response_model=ProveedorResponse, status_code=201)
async def crear(
    datos: ProveedorCreate,
    request: Request,
    usuario: Usuario = Depends(require_permission("proveedores.gestionar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    creado = await contenedor.crear_proveedor_usecase(db).ejecutar(
        razon_social=datos.razon_social,
        ruc=datos.ruc,
        telefono=datos.telefono,
        email=datos.email,
        direccion=datos.direccion,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return ProveedorResponse.desde_entidad(creado)


@router.get("/{proveedor_id}", response_model=ProveedorResponse)
async def obtener(
    proveedor_id: int,
    _usuario: Usuario = Depends(require_permission("proveedores.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    from app.shared.kernel.exceptions import NoEncontradoError
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_proveedor_repository import (
        SqlAlchemyProveedorRepository,
    )

    repo = SqlAlchemyProveedorRepository(db)
    p = await repo.find_by_id(proveedor_id)
    if p is None:
        raise NoEncontradoError("Proveedor no encontrado.")
    return ProveedorResponse.desde_entidad(p)


@router.patch("/{proveedor_id}", response_model=ProveedorResponse)
async def editar(
    proveedor_id: int,
    datos: ProveedorUpdate,
    request: Request,
    usuario: Usuario = Depends(require_permission("proveedores.gestionar")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    # Defensa: rechazar explícitamente deuda_actual
    from app.shared.kernel.exceptions import ValidacionError
    if "deuda_actual" in datos.model_dump(exclude_unset=True):
        raise ValidacionError(
            "deuda_actual solo se modifica vía compras a crédito o pagos."
        )
    cambios = datos.model_dump(exclude_unset=True)
    ip, user_agent = contexto_request(request)
    actualizado = await contenedor.editar_proveedor_usecase(db).ejecutar(
        proveedor_id=proveedor_id,
        cambios=cambios,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    return ProveedorResponse.desde_entidad(actualizado)


@router.post(
    "/{proveedor_id}/compras-credito", response_model=PagoProveedorResponse, status_code=201
)
async def registrar_compra_credito(
    proveedor_id: int,
    datos: PagoProveedorCreate,
    request: Request,
    usuario: Usuario = Depends(require_permission("proveedores.compras_credito")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    pago = await contenedor.registrar_compra_credito_usecase(db).ejecutar(
        proveedor_id=proveedor_id,
        monto=Decimal(str(datos.monto)),
        fecha=datos.fecha,
        concepto=datos.concepto,
        solicitud_ingreso_id=datos.solicitud_ingreso_id,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    # Recargar para devolver deuda_actual
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_proveedor_repository import (
        SqlAlchemyProveedorRepository,
    )
    repo = SqlAlchemyProveedorRepository(db)
    prov = await repo.find_by_id(proveedor_id)
    resp = PagoProveedorResponse.desde_entidad(pago)
    if prov is not None:
        resp.deuda_actual = float(prov.deuda_actual)
    else:
        resp.deuda_actual = 0.0
    return resp


@router.post(
    "/{proveedor_id}/pagos", response_model=PagoProveedorResponse, status_code=201
)
async def registrar_pago(
    proveedor_id: int,
    datos: PagoProveedorCreate,
    request: Request,
    usuario: Usuario = Depends(require_permission("proveedores.pagos")),
    db: AsyncSession = Depends(get_db),
    auditoria=Depends(get_auditoria),
):
    ip, user_agent = contexto_request(request)
    pago = await contenedor.registrar_pago_proveedor_usecase(db).ejecutar(
        proveedor_id=proveedor_id,
        monto=Decimal(str(datos.monto)),
        fecha=datos.fecha,
        concepto=datos.concepto,
        usuario_id=usuario.id,  # type: ignore[union-attr]
        usuario_nombre=usuario.nombre,
        ip=ip,
        user_agent=user_agent,
    )
    from app.modules.modulo_b_inventario.infrastructure.adapters.database.sqlalchemy_proveedor_repository import (
        SqlAlchemyProveedorRepository,
    )
    repo = SqlAlchemyProveedorRepository(db)
    prov = await repo.find_by_id(proveedor_id)
    resp = PagoProveedorResponse.desde_entidad(pago)
    if prov is not None:
        resp.deuda_actual = float(prov.deuda_actual)
    else:
        resp.deuda_actual = 0.0
    return resp


@router.get("/{proveedor_id}/pagos", response_model=PagosPaginadosResponse)
async def listar_pagos(
    proveedor_id: int,
    tipo: str | None = None,
    fecha_desde: date_type | None = None,
    fecha_hasta: date_type | None = None,
    page: int = 1,
    page_size: int = 20,
    _usuario: Usuario = Depends(require_permission("proveedores.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    items, total, deuda, page, page_size, total_pages = await contenedor.listar_pagos_proveedor_usecase(
        db
    ).ejecutar(
        proveedor_id=proveedor_id,
        tipo=tipo,
        fecha_desde=fecha_desde.isoformat() if fecha_desde else None,
        fecha_hasta=fecha_hasta.isoformat() if fecha_hasta else None,
        page=page,
        page_size=page_size,
    )
    return PagosPaginadosResponse(
        items=[PagoProveedorResponse.desde_entidad(p) for p in items],
        deuda_actual=float(deuda) if deuda is not None else 0.0,
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )
