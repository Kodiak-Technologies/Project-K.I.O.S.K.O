# Puerto: contrato para mermas y pérdidas (RF-23, HU-B12, CU-B09b/c, D-14).
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import Merma


class MermaRepositoryPort(ABC):
    @abstractmethod
    async def crear(self, merma: Merma) -> Merma:
        """Inserta con estado='Registrada'; NO toca stock."""

    @abstractmethod
    async def find_by_id(self, merma_id: int) -> Merma | None: ...

    @abstractmethod
    async def find_by_id_for_update(self, merma_id: int) -> Merma | None:
        """SELECT ... FOR UPDATE; se usa en confirmar/rechazar."""

    @abstractmethod
    async def actualizar(self, merma: Merma) -> Merma:
        """Persiste transición de estado + snapshots del confirmador/rechazador."""

    @abstractmethod
    async def actualizar_cabecera(self, merma_id: int, cambios: dict) -> Merma:
        """sdd/modulo-b-aprobaciones-detalle-editar: PATCH parcial sobre la
        cabecera (motivo, observacion, proveedor, producto, cantidad, audit
        triple). Devuelve la entidad refrescada."""

    @abstractmethod
    async def listar_paginado(
        self,
        *,
        estado: str | None = None,
        motivo: str | None = None,
        producto_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Merma], int]:
        """Devuelve (items, total). Filtros opcionales."""
