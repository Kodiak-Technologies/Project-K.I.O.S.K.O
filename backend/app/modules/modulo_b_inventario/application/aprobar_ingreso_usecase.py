# Caso de uso: aprobar una solicitud de ingreso (HU-B07, REQ-APR).
# - SELECT ... FOR UPDATE sobre la solicitud.
# - Por cada línea: UPDATE producto.stock atómico + APPEND movimiento 'ingreso'.
# - UPDATE solicitud a 'Aprobada' con revisado_por.
# - Si rowcount=0 en cualquier UPDATE de stock → ROLLBACK 409.
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    DetalleSolicitud,
    MovimientoInventario,
    SolicitudIngreso,
)
from app.modules.modulo_b_inventario.domain.ports.detalle_solicitud_repository_port import (
    DetalleSolicitudRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.movimiento_inventario_repository_port import (
    MovimientoInventarioRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)


@dataclass
class AprobacionResultado:
    solicitud: SolicitudIngreso
    productos_actualizados: int
    unidades_agregadas: int


class AprobarIngresoUseCase:
    def __init__(
        self,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        detalle_repo: DetalleSolicitudRepositoryPort,
        producto_repo: ProductoRepositoryPort,
        movimiento_repo: MovimientoInventarioRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._solicitudes = solicitud_repo
        self._detalles = detalle_repo
        self._productos = producto_repo
        self._movimientos = movimiento_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        solicitud_id: int,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> AprobacionResultado:
        # 1) FOR UPDATE la solicitud
        solicitud = await self._solicitudes.find_by_id_for_update(solicitud_id)
        if solicitud is None:
            raise NoEncontradoError("La solicitud no existe.")
        if not solicitud.puede_ser_aprobada():
            raise ConflictoError("La solicitud ya fue revisada.")

        # 2) Por cada línea: incrementar stock atómico + APPEND movimiento
        detalles = await self._detalles.listar_por_solicitud(solicitud_id)
        productos_actualizados = 0
        unidades_agregadas = 0
        for d in detalles:
            ok, _stock_actual = await self._productos.incrementar_stock_atomic(
                d.producto_id, d.cantidad
            )
            if not ok:
                # rowcount=0 → stock insuficiente, producto borrado, o error
                raise ConflictoError(
                    f"No se puede sumar {d.cantidad} al producto {d.producto_id}: "
                    "stock insuficiente o producto borrado."
                )
            await self._movimientos.append(
                MovimientoInventario.ingreso(
                    producto_id=d.producto_id,
                    cantidad=d.cantidad,
                    solicitud_ingreso_id=solicitud_id,
                    usuario_id=usuario_id,
                    usuario_nombre=usuario_nombre,
                )
            )
            productos_actualizados += 1
            unidades_agregadas += d.cantidad

        # 3) Transición de estado
        solicitud.aprobar(usuario_id, usuario_nombre)
        await self._solicitudes.actualizar(solicitud)

        await self._auditoria.ejecutar(
            accion="aprobar_ingreso",
            entidad="solicitudes_ingreso",
            usuario_id=usuario_id,
            rol="",
            entidad_id=solicitud_id,
            valor_nuevo={
                "unidades": unidades_agregadas,
                "productos": productos_actualizados,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return AprobacionResultado(
            solicitud=solicitud,
            productos_actualizados=productos_actualizados,
            unidades_agregadas=unidades_agregadas,
        )
