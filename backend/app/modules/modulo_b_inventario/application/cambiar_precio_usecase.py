# Caso de uso: cambiar precio de un producto (HU-B11, REQ-11).
# SELECT ... FOR UPDATE + APPEND historial_precios por cada cambio real.
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import (
    HistorialPrecio,
    Producto,
)
from app.modules.modulo_b_inventario.domain.ports.historial_precio_repository_port import (
    HistorialPrecioRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.producto_repository_port import (
    ProductoRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.value_objects import TipoPrecio
from app.shared.kernel.exceptions import ValidacionError


class CambiarPrecioUseCase:
    def __init__(
        self,
        producto_repo: ProductoRepositoryPort,
        historial_repo: HistorialPrecioRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._productos = producto_repo
        self._historial = historial_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        producto_id: int,
        precio_venta: Decimal | None,
        precio_compra_actual: Decimal | None,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> tuple[Producto, bool, list[HistorialPrecio]]:
        if precio_venta is None and precio_compra_actual is None:
            raise ValidacionError(
                "Debes enviar al menos uno: precio_venta o precio_compra_actual."
            )
        if precio_venta is not None and Decimal(str(precio_venta)) < 0:
            raise ValidacionError("precio_venta no puede ser negativo.")
        if precio_compra_actual is not None and Decimal(str(precio_compra_actual)) < 0:
            raise ValidacionError("precio_compra_actual no puede ser negativo.")

        # El repo hace el SELECT FOR UPDATE y el APPEND al historial.
        producto_actualizado, filas_hist = await self._productos.actualizar_precio(
            producto_id,
            Decimal(str(precio_venta)) if precio_venta is not None else None,
            Decimal(str(precio_compra_actual)) if precio_compra_actual is not None else None,
            usuario_id,
            usuario_nombre,
        )
        historial_registrado = len(filas_hist) > 0

        if historial_registrado:
            await self._auditoria.ejecutar(
                accion="cambiar_precio",
                entidad="productos",
                usuario_id=usuario_id,
                rol="",
                entidad_id=producto_id,
                valor_nuevo={
                    "filas_historial": [
                        {
                            "tipo": str(h.tipo_precio),
                            "anterior": float(h.precio_anterior) if h.precio_anterior is not None else None,
                            "nuevo": float(h.precio_nuevo),
                        }
                        for h in filas_hist
                    ],
                    "precio_venta": float(producto_actualizado.precio),
                    "precio_compra_actual": float(producto_actualizado.precio_compra_actual),
                },
                ip=ip,
                user_agent=user_agent,
            )

        return producto_actualizado, historial_registrado, filas_hist
