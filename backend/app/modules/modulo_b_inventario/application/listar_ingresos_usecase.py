# Caso de uso: listar solicitudes de ingreso (HU-B08, REQ-CONS).
# - ADMIN ve todas, CAJERO solo las propias.
# - Filtros: estado, proveedor, fechas.
from decimal import Decimal

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_b_inventario.domain.entities import SolicitudIngreso
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


class ListarIngresosUseCase:
    def __init__(
        self,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        detalle_repo: DetalleSolicitudRepositoryPort,
    ):
        self._solicitudes = solicitud_repo
        self._detalles = detalle_repo

    async def ejecutar(
        self,
        *,
        estado: str | None = None,
        proveedor_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
        usuario: Usuario | None = None,
    ) -> tuple[list[dict], int, int, int, int]:
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        # Defensa en profundidad (Q5): CAJERO solo ve lo propio
        if usuario is not None and usuario.rol_nombre == "CAJERO":
            items, total = await self._solicitudes.listar_por_solicitante(
                usuario.id,  # type: ignore[union-attr]
                estado=estado,
                proveedor_id=proveedor_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                page=page,
                page_size=page_size,
            )
        else:
            items, total = await self._solicitudes.listar_paginado(
                estado=estado,
                proveedor_id=proveedor_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                page=page,
                page_size=page_size,
            )
        # Cada item: agregados cantidad_productos y monto_total
        resultado: list[dict] = []
        for s in items:
            lineas = s.lineas if s.lineas else await self._detalles.listar_por_solicitud(
                s.id  # type: ignore[arg-type]
            )
            cantidad_productos = sum(l.cantidad for l in lineas)
            monto_total = sum(
                (l.cantidad * l.precio_compra_unitario for l in lineas),
                start=Decimal("0"),
            )
            resultado.append(
                {
                    "solicitud": s,
                    "cantidad_productos": cantidad_productos,
                    "monto_total": float(monto_total),
                }
            )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return resultado, total, page, page_size, total_pages
