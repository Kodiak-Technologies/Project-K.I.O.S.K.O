# Puerto: contrato para persistir/consultar aperturas y cierres de caja.
from abc import ABC, abstractmethod

from app.modules.modulo_c_ventas.domain.entities import TurnoCaja


class CajaRepositoryPort(ABC):
    @abstractmethod
    async def turno_abierto(self) -> TurnoCaja | None:
        """El único turno en estado ABIERTO, o None si la caja está cerrada."""

    @abstractmethod
    async def buscar_por_id(self, turno_id: int) -> TurnoCaja | None: ...

    @abstractmethod
    async def abrir(self, turno: TurnoCaja) -> TurnoCaja: ...

    @abstractmethod
    async def listar(self, limite: int = 30) -> list[TurnoCaja]:
        """Turnos más recientes primero (historial visible para todos los usuarios)."""
