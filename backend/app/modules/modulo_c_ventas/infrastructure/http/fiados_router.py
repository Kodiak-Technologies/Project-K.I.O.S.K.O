# Router HTTP: /fiados/*. Sin lógica de negocio (las reglas viven en
# GestionarFiadosUseCase: quién puede asignar crédito, qué entra a caja, etc.).
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_current_user,
)
from app.modules.modulo_c_ventas import module_container as contenedor
from app.modules.modulo_c_ventas.infrastructure.http.schemas import (
    ActualizarClienteFiadoRequest,
    ClienteFiadoResponse,
    CrearClienteFiadoRequest,
    EstadoCuentaFiadoResponse,
    MovimientoFiadoResponse,
    PagoFiadoRequest,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/fiados", tags=["Fiados"])


@router.get("/clientes", response_model=list[ClienteFiadoResponse])
async def listar(
    buscar: str | None = None,
    incluir_inactivos: bool = False,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clientes = await contenedor.gestionar_fiados_usecase(db).listar(buscar, incluir_inactivos)
    return [ClienteFiadoResponse.desde_entidad(c) for c in clientes]


@router.post("/clientes", response_model=ClienteFiadoResponse, status_code=201)
async def crear(
    datos: CrearClienteFiadoRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    cliente = await contenedor.gestionar_fiados_usecase(db).crear_cliente(
        usuario_id=usuario.id,
        rol=usuario.rol_nombre,
        nombre=datos.nombre,
        telefono=datos.telefono,
        nota=datos.nota,
        limite_mensual=Decimal(str(datos.limite_mensual)) if datos.limite_mensual is not None else None,
        ip=ip,
        user_agent=user_agent,
    )
    return ClienteFiadoResponse.desde_entidad(cliente)


@router.get("/clientes/{cliente_id}", response_model=EstadoCuentaFiadoResponse)
async def estado_de_cuenta(
    cliente_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cliente, movimientos = await contenedor.gestionar_fiados_usecase(db).estado_de_cuenta(cliente_id)
    return EstadoCuentaFiadoResponse(
        cliente=ClienteFiadoResponse.desde_entidad(cliente),
        movimientos=[MovimientoFiadoResponse.desde_entidad(m) for m in movimientos],
    )


@router.patch("/clientes/{cliente_id}", response_model=ClienteFiadoResponse)
async def actualizar(
    cliente_id: int,
    datos: ActualizarClienteFiadoRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # El límite mensual y la desactivación los valida el caso de uso (solo ADMIN).
    ip, user_agent = contexto_request(request)
    cliente = await contenedor.gestionar_fiados_usecase(db).actualizar_cliente(
        usuario_id=usuario.id,
        rol=usuario.rol_nombre,
        cliente_id=cliente_id,
        cambios=datos.model_dump(exclude_unset=True),
        ip=ip,
        user_agent=user_agent,
    )
    return ClienteFiadoResponse.desde_entidad(cliente)


@router.post("/clientes/{cliente_id}/pagos", response_model=MovimientoFiadoResponse, status_code=201)
async def pagar(
    cliente_id: int,
    datos: PagoFiadoRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """El cliente paga lo que debe: entra a la caja del turno ACTUAL."""
    ip, user_agent = contexto_request(request)
    movimiento = await contenedor.gestionar_fiados_usecase(db).registrar_pago(
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        cliente_id=cliente_id,
        monto=Decimal(str(datos.monto)),
        metodo=datos.metodo,
        nota=datos.nota,
        ip=ip,
        user_agent=user_agent,
    )
    return MovimientoFiadoResponse.desde_entidad(movimiento)


@router.post("/clientes/{cliente_id}/creditos", response_model=MovimientoFiadoResponse, status_code=201)
async def credito_pagado(
    cliente_id: int,
    datos: PagoFiadoRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crédito YA pagado (solo ADMIN): queda a favor del cliente y entra a la caja."""
    ip, user_agent = contexto_request(request)
    movimiento = await contenedor.gestionar_fiados_usecase(db).registrar_adelanto(
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        cliente_id=cliente_id,
        monto=Decimal(str(datos.monto)),
        metodo=datos.metodo,
        nota=datos.nota,
        ip=ip,
        user_agent=user_agent,
    )
    return MovimientoFiadoResponse.desde_entidad(movimiento)
