# Router HTTP: /inventario/movimientos — bitácora append-only de variaciones de stock.
from datetime import date as date_type

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    require_permission,
)
from app.modules.modulo_b_inventario import module_container as contenedor
from app.modules.modulo_b_inventario.infrastructure.http.schemas import (
    MovimientoInventarioResponse,
    MovimientosPaginadosResponse,
)
from app.shared.database.session import get_db
from app.shared.http.cursor import codificar_cursor, decodificar_cursor

router = APIRouter(prefix="/inventario/movimientos", tags=["Inventario - Movimientos"])


@router.get("", response_model=MovimientosPaginadosResponse)
async def listar(
    producto_id: int | None = None,
    tipo: str | None = None,
    fecha_desde: date_type | None = None,
    fecha_hasta: date_type | None = None,
    page: int = 1,
    page_size: int = 20,
    cursor: str | None = None,
    _usuario: Usuario = Depends(require_permission("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    items, total, page, page_size, total_pages = await contenedor.listar_movimientos_inventario_usecase(
        db
    ).ejecutar(
        producto_id=producto_id,
        tipo=tipo,
        fecha_desde=fecha_desde.isoformat() if fecha_desde else None,
        fecha_hasta=fecha_hasta.isoformat() if fecha_hasta else None,
        page=page,
        page_size=page_size,
        cursor=decodificar_cursor(cursor) if cursor else None,
    )
    # Página completa ⇒ asumimos que hay más; página corta ⇒ se acabó.
    siguiente = (
        codificar_cursor(items[-1].created_at, items[-1].id)  # type: ignore[arg-type]
        if len(items) == page_size
        else None
    )
    return MovimientosPaginadosResponse(
        items=[
            MovimientoInventarioResponse(
                id=m.id,  # type: ignore[arg-type]
                producto_id=m.producto_id,
                producto_nombre=m.producto_nombre,
                producto_codigo=m.producto_codigo,
                cantidad=m.cantidad,
                tipo=str(m.tipo),
                motivo=m.motivo,
                solicitud_ingreso_id=m.solicitud_ingreso_id,
                merma_id=m.merma_id,
                registrado_por_nombre=m.registrado_por_nombre,
                created_at=m.created_at,
            )
            for m in items
        ],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
        siguiente_cursor=siguiente,
    )
