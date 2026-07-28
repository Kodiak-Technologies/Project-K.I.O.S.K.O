# Caso de uso: ajuste manual de stock desde el catálogo (solo ADMIN).
#
# Reemplaza al flujo de mermas: en vez de registrar una merma y confirmarla, la
# administradora corrige el stock directamente (+/-) dejando SIEMPRE un motivo y
# un asiento en `movimientos_inventario` (tipo='ajuste', D-07).
#
# El cajero NO puede ajustar: para él, el stock solo sube aprobando una solicitud
# de ingreso (HU-B06/B07) y solo baja vendiendo (HU-B10).
from dataclasses import dataclass

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    MovimientoInventario,
    Producto,
)
from app.modules.modulo_b_inventario.domain.ports.movimiento_inventario_repository_port import (
    MovimientoInventarioRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)


@dataclass
class AjusteResultado:
    producto: Producto
    stock_anterior: int
    stock_actual: int
    delta: int


class AjustarStockUseCase:
    MOTIVO_MIN = 3
    MOTIVO_MAX = 200

    def __init__(
        self,
        producto_repo: ProductoRepositoryPort,
        movimiento_repo: MovimientoInventarioRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
        notificador=None,
    ):
        self._productos = producto_repo
        self._movimientos = movimiento_repo
        self._auditoria = auditoria
        # Opcional para los tests unitarios; el contenedor siempre lo inyecta.
        self._notificador = notificador

    async def ejecutar(
        self,
        *,
        producto_id: int,
        delta: int,
        motivo: str,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> AjusteResultado:
        if delta == 0:
            raise ValidacionError("El ajuste debe ser distinto de 0.")
        motivo_limpio = (motivo or "").strip()
        if len(motivo_limpio) < self.MOTIVO_MIN:
            raise ValidacionError(
                "Indica el motivo del ajuste (mínimo 3 caracteres).",
                code="MOTIVO_REQUERIDO",
            )
        if len(motivo_limpio) > self.MOTIVO_MAX:
            raise ValidacionError("El motivo es demasiado largo (máximo 200).")

        producto = await self._productos.buscar_por_id(producto_id)
        if producto is None or producto.deleted_at is not None:
            raise NoEncontradoError("Producto no encontrado.")

        stock_anterior = producto.stock
        # UPDATE atómico: si otra operación se lleva las últimas unidades, esta
        # falla en vez de dejar el stock negativo (RF-08).
        ok, stock_actual = await self._productos.incrementar_stock_atomic(
            producto_id, delta
        )
        if not ok:
            raise ConflictoError(
                f"No se puede descontar {abs(delta)}: el stock disponible es "
                f"{stock_anterior}.",
                code="STOCK_INSUFICIENTE",
            )

        await self._movimientos.append(
            MovimientoInventario.ajuste(
                producto_id=producto_id,
                cantidad=delta,
                motivo=motivo_limpio,
                usuario_id=usuario_id,
                usuario_nombre=usuario_nombre,
            )
        )
        await self._auditoria.ejecutar(
            accion="ajustar_stock",
            entidad="productos",
            usuario_id=usuario_id,
            rol="",
            entidad_id=producto_id,
            motivo=motivo_limpio,
            valor_anterior={"stock": stock_anterior},
            valor_nuevo={"stock": stock_actual, "delta": delta},
            ip=ip,
            user_agent=user_agent,
        )
        actualizado = await self._productos.buscar_por_id(producto_id)
        await self._avisar_si_bajo_minimo(actualizado)
        return AjusteResultado(
            producto=actualizado,  # type: ignore[arg-type]
            stock_anterior=stock_anterior,
            stock_actual=stock_actual,  # type: ignore[arg-type]
            delta=delta,
        )

    async def _avisar_si_bajo_minimo(self, producto: Producto | None) -> None:
        """HU-B13/RF-24: alerta única por producto hasta su reposición."""
        if self._notificador is None or producto is None:
            return
        if not producto.requiere_reposicion():
            return
        # El UPDATE condicional garantiza un solo aviso aunque haya concurrencia.
        if not await self._productos.marcar_alerta_si_nueva(producto.id):
            return
        from app.modules.modulo_d_documentos.domain.value_objects import TipoNotificacion

        await self._notificador.avisar(
            TipoNotificacion.STOCK_BAJO,
            f"Stock bajo: {producto.nombre}",
            f"Quedan {producto.stock} unidades (mínimo {producto.stock_minimo}). "
            "Conviene reponer.",
            entidad_origen="productos",
            entidad_id=producto.id,
            producto_id=producto.id,
        )
