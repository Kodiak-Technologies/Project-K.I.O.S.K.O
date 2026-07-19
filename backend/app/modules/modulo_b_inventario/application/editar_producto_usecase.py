# Caso de uso: editar un producto existente (no toca precios).
# Cambio de precio va por `CambiarPrecioUseCase`.
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)


class EditarProductoUseCase:
    def __init__(
        self,
        producto_repo: ProductoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._productos = producto_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        producto_id: int,
        cambios: dict,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Producto:
        # Si vienen precio o precio_compra_actual, los rechazamos (delegamos a /precio)
        if "precio" in cambios or "precio_compra_actual" in cambios:
            from app.shared.kernel.exceptions import ValidacionError
            raise ValidacionError(
                "Use PATCH /productos/{id}/precio para cambiar precios."
            )
        anterior = await self._productos.buscar_por_id(producto_id)
        actualizado = await self._productos.actualizar_general(
            producto_id, cambios, usuario_id, usuario_nombre
        )
        await self._auditoria.ejecutar(
            accion="producto_editado",
            entidad="productos",
            usuario_id=usuario_id,
            rol="",
            entidad_id=producto_id,
            valor_anterior={
                "nombre": anterior.nombre if anterior else None,
                "stock_minimo": anterior.stock_minimo if anterior else None,
                "activo": anterior.activo if anterior else None,
            } if anterior else None,
            valor_nuevo={
                k: (float(v) if isinstance(v, Decimal) else v)
                for k, v in cambios.items()
                if v is not None
            },
            ip=ip,
            user_agent=user_agent,
        )
        return actualizado
