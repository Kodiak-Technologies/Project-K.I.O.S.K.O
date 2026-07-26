# Caso de uso: anular una venta completa o devolver ítems (RF-22).
#
# La venta NUNCA se borra: se genera un movimiento de reverso (Anulacion) que
# repone el stock, registra cuánto efectivo salió de la caja del turno ACTUAL y
# deja rastro (quién, cuándo, motivo) visible para la administradora en su panel
# de caja y en la bitácora. Lo puede hacer el cajero: el rastro es el control.
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_c_ventas.domain.entities import Anulacion, Venta
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.producto_stock_port import ProductoStockPort
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.modules.modulo_c_ventas.domain.value_objects import (
    REVERSO_ANULACION,
    REVERSO_DEVOLUCION,
    VENTA_ANULADA,
    VENTA_DEVUELTA_PARCIAL,
    monto_dinero,
)
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError, ValidacionError


class AnularVentaUseCase:
    """Anulación total y devolución parcial comparten la misma mecánica de reverso."""

    def __init__(
        self,
        venta_repo: VentaRepositoryPort,
        caja_repo: CajaRepositoryPort,
        stock: ProductoStockPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._ventas = venta_repo
        self._caja = caja_repo
        self._stock = stock
        self._auditoria = auditoria

    async def _preparar(self, venta_id: int, motivo: str) -> tuple[Venta, int, Decimal]:
        if not motivo.strip():
            raise ValidacionError("Indica el motivo: queda registrado para la administradora.")
        venta = await self._ventas.buscar_por_id(venta_id)
        if venta is None:
            raise NoEncontradoError("Venta no encontrada.")
        if venta.anulada:
            raise ConflictoError("Esta venta ya fue anulada.")
        # El reverso ajusta la caja del turno ACTUAL: sin turno abierto no hay
        # de dónde devolver el dinero.
        turno = await self._caja.turno_abierto()
        if turno is None:
            raise ConflictoError("Abre un turno de caja para registrar el reverso.")
        # Efectivo de la venta que aún no ha sido devuelto en reversos anteriores.
        previas = await self._ventas.anulaciones_de_venta(venta_id)
        efectivo_disponible = venta.total_efectivo - sum(
            (a.efectivo_devuelto for a in previas), Decimal("0")
        )
        return venta, turno.id, max(efectivo_disponible, Decimal("0"))

    async def anular(
        self,
        venta_id: int,
        usuario_id: int,
        nombre_usuario: str,
        rol: str,
        motivo: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Venta:
        venta, turno_id, efectivo_disponible = await self._preparar(venta_id, motivo)

        # Reponer TODO lo que sigue vendido (lo ya devuelto parcialmente no se repone dos veces).
        items = []
        monto = Decimal("0")
        for detalle in venta.detalles:
            restante = detalle.cantidad - detalle.cantidad_devuelta
            if restante <= 0:
                continue
            await self._stock.reponer_stock(
                detalle.producto_id, restante, usuario_id, nombre_usuario,
                motivo=f"Anulación de venta #{venta_id}",
            )
            await self._ventas.registrar_devolucion_detalle(detalle.id, restante)
            items.append(
                {"producto_id": detalle.producto_id, "nombre": detalle.nombre, "cantidad": restante}
            )
            monto += detalle.precio_unitario * restante

        monto = monto_dinero(monto)
        efectivo_devuelto = min(monto, efectivo_disponible)
        await self._ventas.actualizar_estado(venta_id, VENTA_ANULADA, motivo.strip())
        anulacion = await self._ventas.crear_anulacion(
            Anulacion(
                id=None, venta_id=venta_id, turno_id=turno_id, tipo=REVERSO_ANULACION,
                usuario_id=usuario_id, realizado_por=nombre_usuario, motivo=motivo.strip(),
                monto=monto, efectivo_devuelto=efectivo_devuelto, items=items,
            )
        )
        await self._auditoria.ejecutar(
            accion="venta_anulada", entidad="ventas", entidad_id=venta_id,
            usuario_id=usuario_id, rol=rol,
            valor_anterior={"estado": venta.estado, "total": float(venta.total)},
            valor_nuevo={
                "estado": VENTA_ANULADA,
                "monto_revertido": float(monto),
                "efectivo_devuelto": float(efectivo_devuelto),
                "reverso_id": anulacion.id,
            },
            motivo=motivo.strip(), ip=ip, user_agent=user_agent,
        )
        return await self._ventas.buscar_por_id(venta_id)

    async def devolver(
        self,
        venta_id: int,
        usuario_id: int,
        nombre_usuario: str,
        rol: str,
        items: list[tuple[int, int]],  # (detalle_id, cantidad)
        motivo: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Venta:
        venta, turno_id, efectivo_disponible = await self._preparar(venta_id, motivo)
        if not items:
            raise ValidacionError("Indica qué productos se devuelven.")

        detalles_por_id = {d.id: d for d in venta.detalles}
        items_rastro = []
        monto = Decimal("0")
        for detalle_id, cantidad in items:
            detalle = detalles_por_id.get(detalle_id)
            if detalle is None:
                raise ValidacionError(f"La línea {detalle_id} no pertenece a esta venta.")
            restante = detalle.cantidad - detalle.cantidad_devuelta
            if cantidad <= 0 or cantidad > restante:
                raise ValidacionError(
                    f"De '{detalle.nombre}' solo quedan {restante} unidades por devolver."
                )
            await self._stock.reponer_stock(
                detalle.producto_id, cantidad, usuario_id, nombre_usuario,
                motivo=f"Devolución de venta #{venta_id}",
            )
            await self._ventas.registrar_devolucion_detalle(detalle_id, cantidad)
            items_rastro.append(
                {"producto_id": detalle.producto_id, "nombre": detalle.nombre, "cantidad": cantidad}
            )
            monto += detalle.precio_unitario * cantidad

        monto = monto_dinero(monto)
        efectivo_devuelto = min(monto, efectivo_disponible)
        await self._ventas.actualizar_estado(venta_id, VENTA_DEVUELTA_PARCIAL)
        anulacion = await self._ventas.crear_anulacion(
            Anulacion(
                id=None, venta_id=venta_id, turno_id=turno_id, tipo=REVERSO_DEVOLUCION,
                usuario_id=usuario_id, realizado_por=nombre_usuario, motivo=motivo.strip(),
                monto=monto, efectivo_devuelto=efectivo_devuelto, items=items_rastro,
            )
        )
        await self._auditoria.ejecutar(
            accion="venta_devuelta", entidad="ventas", entidad_id=venta_id,
            usuario_id=usuario_id, rol=rol,
            valor_nuevo={
                "items": items_rastro,
                "monto_devuelto": float(monto),
                "efectivo_devuelto": float(efectivo_devuelto),
                "reverso_id": anulacion.id,
            },
            motivo=motivo.strip(), ip=ip, user_agent=user_agent,
        )
        return await self._ventas.buscar_por_id(venta_id)
