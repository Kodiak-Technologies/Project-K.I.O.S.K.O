# Caso de uso: confirmar una merma (CU-B09b, REQ-CONF).
# - SELECT ... FOR UPDATE.
# - UPDATE producto SET stock = stock - :cant WHERE stock >= :cant (409 si rowcount=0).
# - APPEND movimiento tipo='merma', cantidad=-merma.cantidad, merma_id.
# - UPDATE merma SET estado='Confirmada'.
from dataclasses import dataclass

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    Merma,
    MovimientoInventario,
)
from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
    MermaRepositoryPort,
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
)


@dataclass
class ConfirmacionMermaResultado:
    merma: Merma
    stock_actualizado: int


class ConfirmarMermaUseCase:
    def __init__(
        self,
        merma_repo: MermaRepositoryPort,
        producto_repo: ProductoRepositoryPort,
        movimiento_repo: MovimientoInventarioRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._mermas = merma_repo
        self._productos = producto_repo
        self._movimientos = movimiento_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        merma_id: int,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> ConfirmacionMermaResultado:
        merma = await self._mermas.find_by_id_for_update(merma_id)
        if merma is None:
            raise NoEncontradoError("La merma no existe.")
        if not merma.puede_ser_confirmada():
            raise ConflictoError("La merma ya fue revisada.")

        # UPDATE atómico: stock = stock - :cant WHERE stock >= :cant
        ok, stock_actual = await self._productos.incrementar_stock_atomic(
            merma.producto_id, -merma.cantidad
        )
        if not ok:
            # rowcount=0 → stock insuficiente o producto borrado
            producto = await self._productos.buscar_por_id(merma.producto_id)
            if producto is None or producto.deleted_at is not None:
                raise NoEncontradoError("El producto ya no existe.")
            raise ConflictoError("Stock insuficiente.")

        # APPEND movimiento
        await self._movimientos.append(
            MovimientoInventario.merma(
                producto_id=merma.producto_id,
                cantidad=merma.cantidad,
                merma_id=merma_id,
                motivo=str(merma.motivo),
                usuario_id=usuario_id,
                usuario_nombre=usuario_nombre,
            )
        )

        # UPDATE estado merma
        merma.confirmar(usuario_id, usuario_nombre)
        await self._mermas.actualizar(merma)

        await self._auditoria.ejecutar(
            accion="confirmar_merma",
            entidad="mermas",
            usuario_id=usuario_id,
            rol="",
            entidad_id=merma_id,
            valor_nuevo={
                "cantidad": merma.cantidad,
                "producto_id": merma.producto_id,
                "stock_actualizado": stock_actual,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return ConfirmacionMermaResultado(
            merma=merma, stock_actualizado=stock_actual  # type: ignore[arg-type]
        )
