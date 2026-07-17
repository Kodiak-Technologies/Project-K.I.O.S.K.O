# Router HTTP: /caja/*. Sin lógica de negocio.
from decimal import Decimal

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
    AbrirCajaRequest,
    AnulacionResponse,
    CerrarCajaRequest,
    MovimientosTurnoResponse,
    ResumenCajaResponse,
    TurnoCajaResponse,
    VentaResponse,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/caja", tags=["Caja"])


@router.get("/turno-actual", response_model=TurnoCajaResponse | None)
async def turno_actual(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    turno = await contenedor.consultar_caja_usecase(db).turno_actual()
    return TurnoCajaResponse.desde_entidad(turno) if turno else None


@router.post("/abrir", response_model=TurnoCajaResponse, status_code=201)
async def abrir(
    datos: AbrirCajaRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("caja.abrir_turno")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    turno = await contenedor.abrir_caja_usecase(db).ejecutar(
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        monto_inicial=Decimal(str(datos.monto_inicial)),
        ip=ip,
        user_agent=user_agent,
    )
    return TurnoCajaResponse.desde_entidad(turno)


@router.get("/resumen", response_model=ResumenCajaResponse)
async def resumen(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """La sugerencia de cierre (RF-17): efectivo esperado + desglose por método.
    Lo digital (Yape, tarjeta...) se muestra aparte: no está físicamente en caja."""
    datos = await contenedor.consultar_caja_usecase(db).resumen()
    return ResumenCajaResponse.desde_entidad(datos)


@router.post("/cerrar", response_model=TurnoCajaResponse)
async def cerrar(
    datos: CerrarCajaRequest,
    request: Request,
    usuario: Usuario = Depends(require_permission("caja.cerrar_turno")),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    turno, arqueo = await contenedor.cerrar_caja_usecase(db).ejecutar(
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre,
        rol=usuario.rol_nombre,
        monto_final=Decimal(str(datos.monto_final)),
        comentario=datos.comentario,
        ip=ip,
        user_agent=user_agent,
    )
    return TurnoCajaResponse.desde_entidad(turno, arqueo)


@router.get("/turnos", response_model=list[TurnoCajaResponse])
async def historial(
    limite: int = 30,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Visible para TODOS los usuarios: el cajero entrante ve con cuánto abrió y
    # cerró el turno anterior; la administradora supervisa a todos por igual.
    turnos = await contenedor.consultar_caja_usecase(db).historial(min(limite, 100))
    return [TurnoCajaResponse.desde_entidad(t, a) for t, a in turnos]


@router.get("/turnos/{turno_id}/movimientos", response_model=MovimientosTurnoResponse)
async def movimientos(
    turno_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """El RASTRO del turno (HU-C08): ventas, anulaciones/devoluciones y abonos
    de fiado con quién/cuándo/motivo. Es el modal del panel de la administradora."""
    ventas, reversos, abonos = await contenedor.consultar_caja_usecase(db).movimientos(turno_id)
    return MovimientosTurnoResponse(
        ventas=[VentaResponse.desde_entidad(v) for v in ventas],
        reversos=[AnulacionResponse.desde_entidad(r) for r in reversos],
        abonos=abonos,
    )
