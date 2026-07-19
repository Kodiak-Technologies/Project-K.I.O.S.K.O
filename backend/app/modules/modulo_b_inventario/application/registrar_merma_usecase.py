# Caso de uso: registrar una merma (HU-B12, REQ-MER).
# - Crea merma con estado='Registrada' (default).
# - NO toca stock, NO crea movimiento.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
    MermaRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import EstadoMerma, MotivoMerma
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class RegistrarMermaUseCase:
    def __init__(
        self,
        merma_repo: MermaRepositoryPort,
        producto_repo: ProductoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._mermas = merma_repo
        self._productos = producto_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        *,
        producto_id: int,
        cantidad: int,
        motivo: str,
        observacion: str | None,
        proveedor_id: int | None,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Merma:
        if cantidad is None or cantidad <= 0:
            raise ValidacionError("La cantidad debe ser mayor a 0.")
        # VO valida pertenencia del motivo
        motivo_vo = MotivoMerma(motivo)
        producto = await self._productos.buscar_por_id(producto_id)
        if producto is None or producto.deleted_at is not None:
            raise NoEncontradoError("El producto no existe.")
        if not producto.activo:
            raise ValidacionError("El producto está inactivo.")
        creada = await self._mermas.crear(
            Merma(
                id=None,
                producto_id=producto_id,
                cantidad=cantidad,
                motivo=motivo_vo,
                registrado_por=usuario_id,
                registrado_por_nombre=usuario_nombre,
                estado=EstadoMerma("Registrada"),
                observacion=observacion,
                proveedor_id=proveedor_id,
            )
        )
        await self._auditoria.ejecutar(
            accion="merma_registrada",
            entidad="mermas",
            usuario_id=usuario_id,
            rol="",
            entidad_id=creada.id,
            valor_nuevo={
                "producto_id": producto_id,
                "cantidad": cantidad,
                "motivo": motivo,
                "observacion": observacion,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return creada
