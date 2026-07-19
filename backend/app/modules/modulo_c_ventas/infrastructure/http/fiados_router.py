# Router HTTP: /clientes/* y /fiados/*. Cuentas por cobrar del barrio (RF-28).
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
    AbonoResponse,
    ActualizarClienteRequest,
    ClienteResponse,
    CrearClienteRequest,
    FiadoResponse,
    LimiteCreditoRequest,
    RegistrarAbonoRequest,
)
from app.shared.database.session import get_db

router = APIRouter(tags=["Fiados"])


# ---------- Clientes ----------
@router.get("/clientes", response_model=list[ClienteResponse])
async def listar_clientes(
    q: str | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clientes = await contenedor.gestionar_clientes_usecase(db).listar(q)
    return [ClienteResponse.desde_entidad(c) for c in clientes]


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
async def crear_cliente(
    datos: CrearClienteRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("clientes.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    creado = await contenedor.gestionar_clientes_usecase(db).crear(
        usuario_id=usuario.id, rol=usuario.rol_nombre,
        nombre=datos.nombre, alias=datos.alias, telefono=datos.telefono,
        ip=ip, user_agent=user_agent,
    )
    return ClienteResponse.desde_entidad(creado)


@router.patch("/clientes/{cliente_id}", response_model=ClienteResponse)
async def actualizar_cliente(
    cliente_id: int,
    datos: ActualizarClienteRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("clientes.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    actualizado = await contenedor.gestionar_clientes_usecase(db).actualizar(
        usuario_id=usuario.id, rol=usuario.rol_nombre,
        cliente_id=cliente_id, cambios=datos.model_dump(exclude_unset=True),
        ip=ip, user_agent=user_agent,
    )
    return ClienteResponse.desde_entidad(actualizado)


@router.patch("/clientes/{cliente_id}/limite-credito", response_model=ClienteResponse)
async def fijar_limite_credito(
    cliente_id: int,
    datos: LimiteCreditoRequest,
    request: Request,
    # Solo la administradora fija límites de crédito (RF-28).
    usuario: Usuario = Depends(require_permission("clientes.limite_credito")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    actualizado = await contenedor.gestionar_clientes_usecase(db).actualizar(
        usuario_id=usuario.id, rol=usuario.rol_nombre,
        cliente_id=cliente_id, cambios={"limite_credito": datos.limite_credito},
        ip=ip, user_agent=user_agent,
    )
    return ClienteResponse.desde_entidad(actualizado)


# ---------- Fiados y abonos ----------
@router.get("/fiados", response_model=list[FiadoResponse])
async def listar_fiados(
    cliente_id: int | None = None,
    pendientes: bool = True,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Reporte de deudas por cliente: el frontend agrupa por `cliente`.
    fiados = await contenedor.consultar_fiados_usecase(db).listar(cliente_id, pendientes)
    return [FiadoResponse.desde_entidad(f) for f in fiados]


@router.get("/fiados/{fiado_id}/abonos", response_model=list[AbonoResponse])
async def abonos_de_fiado(
    fiado_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    abonos = await contenedor.consultar_fiados_usecase(db).abonos(fiado_id)
    return [AbonoResponse.desde_entidad(a) for a in abonos]


@router.post("/fiados/{fiado_id}/abonos", response_model=FiadoResponse, status_code=201)
async def registrar_abono(
    fiado_id: int,
    datos: RegistrarAbonoRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("fiados.abonar")),
    db: AsyncSession = Depends(get_db),
):
    # El abono entra a la caja del turno abierto; si es efectivo, cuenta en el arqueo.
    ip, user_agent = contexto_request(request)
    fiado = await contenedor.registrar_abono_usecase(db).ejecutar(
        fiado_id=fiado_id,
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        monto=datos.monto,
        codigo_metodo=datos.metodo,
        ip=ip,
        user_agent=user_agent,
    )
    return FiadoResponse.desde_entidad(fiado)
