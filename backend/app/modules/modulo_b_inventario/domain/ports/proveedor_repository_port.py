# Puerto: contrato para el maestro de proveedores con control de deuda (RF-27, HU-B14, D-12).
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import Proveedor


class ProveedorRepositoryPort(ABC):
    @abstractmethod
    async def crear(self, proveedor: Proveedor) -> Proveedor:
        """Inserta con deuda_actual=0."""

    @abstractmethod
    async def find_by_id(self, proveedor_id: int) -> Proveedor | None: ...

    @abstractmethod
    async def find_by_id_for_update(self, proveedor_id: int) -> Proveedor | None:
        """SELECT ... FOR UPDATE; se usa en registrar compra crédito y pago."""

    @abstractmethod
    async def actualizar(self, proveedor: Proveedor) -> Proveedor:
        """Persiste cambios NO sensibles a deuda_actual (la deuda se cambia con
        `incrementar_deuda_atomic` dentro de la misma transacción que `pagos_proveedor`)."""

    @abstractmethod
    async def listar_paginado(
        self,
        *,
        search: str | None = None,
        solo_con_deuda: bool = False,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Proveedor], int]:
        """Devuelve (items, total). Filtros opcionales."""

    @abstractmethod
    async def find_by_ruc(self, ruc: str) -> Proveedor | None:
        """Búsqueda por RUC. Usado para validar unicidad parcial al crear."""

    @abstractmethod
    async def incrementar_deuda_atomic(self, proveedor_id: int, delta) -> bool:
        """UPDATE proveedores SET deuda_actual = deuda_actual + :delta WHERE id=:id
        AND deuda_actual + :delta >= 0. Devuelve True si se afectó 1 fila."""
