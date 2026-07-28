# Puerto: contrato para el historial de pagos/compras a crédito (HU-B14, D-12, D-15).
# Append-only por convención: el adaptador NO expone actualizar/eliminar.
from abc import ABC, abstractmethod
from decimal import Decimal

from app.modules.modulo_b_inventario.domain.entities import PagoProveedor


class PagoProveedorRepositoryPort(ABC):
    @abstractmethod
    async def crear(self, pago: PagoProveedor) -> PagoProveedor:
        """Inserta en la misma transacción que el cambio de deuda_actual del proveedor."""

    @abstractmethod
    async def listar_por_proveedor(
        self,
        proveedor_id: int,
        *,
        tipo: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PagoProveedor], int]:
        """Devuelve (items, total) ordenado por fecha DESC, created_at DESC."""

    @abstractmethod
    async def sum_tipo(self, proveedor_id: int, tipo: str) -> Decimal:
        """Suma los montos del tipo ('compra_credito' | 'pago') para un proveedor
        (excluyendo soft-deleted). Usado en tests de invariante de deuda."""
