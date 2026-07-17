# Puerto: contrato para persistir/consultar aperturas y cierres de caja.
from abc import ABC, abstractmethod
from decimal import Decimal

from app.modules.modulo_c_ventas.domain.entities import ArqueoCaja, TurnoCaja


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

    @abstractmethod
    async def cerrar(
        self,
        turno_id: int,
        monto_final: Decimal,
        usuario_cierre_id: int,
        cerrado_por: str,
    ) -> TurnoCaja: ...

    @abstractmethod
    async def guardar_arqueo(self, arqueo: ArqueoCaja) -> ArqueoCaja: ...

    @abstractmethod
    async def arqueos_por_turno(self, turno_ids: list[int]) -> dict[int, ArqueoCaja]:
        """Arqueos de los turnos indicados, indexados por turno_id."""

    @abstractmethod
    async def totales_de_turno(self, turno_id: int) -> dict:
        """Totales del turno para el arqueo (RF-17):
        - ventas_efectivo: dinero FÍSICO que entró por ventas del turno
        - totales_por_metodo: lo vendido desglosado por método (informativo)
        - total_vendido / numero_ventas
        - devoluciones_efectivo: dinero que salió del cajón por reversos (HU-C08)
        - abonos_efectivo: fiados cobrados en efectivo durante el turno (HU-C09)
        """
