# Caso de uso: eliminar un producto del catálogo (solo ADMIN, con contraseña).
#
# Borrado LÓGICO (`deleted_at`), no físico: el producto está referenciado por
# ventas, movimientos, historial de precios y líneas de ingreso con FKs
# `ON DELETE RESTRICT`. Borrarlo de verdad rompería el histórico contable —y la
# BD directamente lo rechazaría. Un producto eliminado desaparece del catálogo,
# de las búsquedas y del POS, pero sus movimientos siguen siendo auditables.
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Producto
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.shared.kernel.exceptions import NoEncontradoError


class EliminarProductoUseCase:
    def __init__(
        self,
        producto_repo: ProductoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._productos = producto_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        *,
        producto_id: int,
        usuario_id: int,
        usuario_nombre: str,
        motivo: str | None = None,
        ip: str = "",
        user_agent: str = "",
    ) -> Producto:
        producto = await self._productos.buscar_por_id(producto_id)
        if producto is None or producto.deleted_at is not None:
            raise NoEncontradoError("Producto no encontrado.")

        eliminado = await self._productos.eliminar(producto_id, usuario_id)
        await self._auditoria.ejecutar(
            accion="producto_eliminado",
            entidad="productos",
            usuario_id=usuario_id,
            rol="",
            entidad_id=producto_id,
            motivo=(motivo or "").strip() or None,
            valor_anterior={
                "codigo": producto.codigo,
                "nombre": producto.nombre,
                "stock": producto.stock,
                "precio": float(producto.precio),
            },
            ip=ip,
            user_agent=user_agent,
        )
        return eliminado
