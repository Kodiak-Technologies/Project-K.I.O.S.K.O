# Puerto: contrato para las líneas (detalle) de una solicitud de ingreso.
# Sin soft delete: la línea no existe sin su cabecera (ON DELETE CASCADE en BD).
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import DetalleSolicitud


class DetalleSolicitudRepositoryPort(ABC):
    @abstractmethod
    async def crear_bulk(self, detalles: list[DetalleSolicitud]) -> list[DetalleSolicitud]:
        """Inserta todas las líneas en una sola operación."""

    @abstractmethod
    async def listar_por_solicitud(self, solicitud_id: int) -> list[DetalleSolicitud]: ...

    @abstractmethod
    async def eliminar_por_solicitud(self, solicitud_id: int) -> None:
        """Útil para rollback explícito en la transacción de creación."""
