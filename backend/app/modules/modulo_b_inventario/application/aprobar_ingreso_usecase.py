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
    monto_total: Decimal = Decimal("0")
    credito_registrado: bool = False


class AprobarIngresoUseCase:
    def __init__(
        self,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        detalle_repo: DetalleSolicitudRepositoryPort,
        producto_repo: ProductoRepositoryPort,
        movimiento_repo: MovimientoInventarioRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
        compra_credito_usecase=None,
    ):
        self._solicitudes = solicitud_repo
        self._detalles = detalle_repo
        self._productos = producto_repo
        self._movimientos = movimiento_repo
        self._auditoria = auditoria
        # Opcional (los tests unitarios no lo inyectan): permite cargar la
        # compra a crédito del proveedor en la MISMA transacción (HU-B14).
        self._compra_credito = compra_credito_usecase

    async def ejecutar(
        self,
        solicitud_id: int,
        usuario_id: int,
        usuario_nombre: str,
        registrar_credito: bool = False,
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
        monto_total = Decimal("0")
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
            # HU-B05/HU-B11: el precio de compra de la boleta pasa a ser el
            # precio de compra vigente del producto y queda en el historial
            # (antes se guardaba en el detalle y nunca llegaba al catálogo).
            await self._productos.actualizar_precio(
                d.producto_id,
                None,
                Decimal(str(d.precio_compra_unitario)),
                usuario_id,
                usuario_nombre,
            )
            productos_actualizados += 1
            unidades_agregadas += d.cantidad
            monto_total += Decimal(str(d.cantidad)) * Decimal(
                str(d.precio_compra_unitario)
            )

        # 3) Transición de estado
        solicitud.aprobar(usuario_id, usuario_nombre)
        await self._solicitudes.actualizar(solicitud)

        # 4) HU-B14 (opcional): cargar la compra a la deuda del proveedor en la
        #    misma transacción, dejando el vínculo con la solicitud.
        credito_registrado = False
        if registrar_credito and monto_total > 0:
            if solicitud.proveedor_id is None:
                raise ValidacionError(
                    "La solicitud no tiene proveedor: no se puede registrar la "
                    "compra a crédito."
                )
            if self._compra_credito is not None:
                from datetime import date as _date

                await self._compra_credito.ejecutar(
                    proveedor_id=solicitud.proveedor_id,
                    monto=monto_total,
                    fecha=_date.today(),
                    concepto=f"Ingreso de mercadería #{solicitud_id}",
                    solicitud_ingreso_id=solicitud_id,
                    usuario_id=usuario_id,
                    usuario_nombre=usuario_nombre,
                    ip=ip,
                    user_agent=user_agent,
                )
                credito_registrado = True

        await self._auditoria.ejecutar(
            accion="aprobar_ingreso",
            entidad="solicitudes_ingreso",
            usuario_id=usuario_id,
            rol="",
            entidad_id=solicitud_id,
            valor_nuevo={
                "unidades": unidades_agregadas,
                "productos": productos_actualizados,
                "monto_total": float(monto_total),
                "credito_registrado": credito_registrado,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return AprobacionResultado(
            solicitud=solicitud,
            productos_actualizados=productos_actualizados,
            unidades_agregadas=unidades_agregadas,
            monto_total=monto_total,
            credito_registrado=credito_registrado,
        )
