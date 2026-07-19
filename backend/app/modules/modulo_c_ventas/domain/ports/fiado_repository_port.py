# Puerto: contrato para clientes, fiados (cuentas por cobrar) y abonos (RF-28).
from abc import ABC, abstractmethod
from decimal import Decimal

from app.modules.modulo_c_ventas.domain.entities import Abono, Cliente, Fiado


class FiadoRepositoryPort(ABC):
    # ---- Clientes ----
    @abstractmethod
    async def listar_clientes(self, busqueda: str | None = None) -> list[Cliente]: ...

    @abstractmethod
    async def buscar_cliente(self, cliente_id: int) -> Cliente | None: ...

    @abstractmethod
    async def crear_cliente(self, cliente: Cliente) -> Cliente: ...

    @abstractmethod
    async def actualizar_cliente(self, cliente_id: int, cambios: dict) -> Cliente: ...

    # ---- Fiados ----
    @abstractmethod
    async def crear_fiado(self, fiado: Fiado) -> Fiado: ...

    @abstractmethod
    async def buscar_fiado(self, fiado_id: int) -> Fiado | None: ...

    @abstractmethod
    async def listar_fiados(
        self, cliente_id: int | None = None, solo_pendientes: bool = True
    ) -> list[Fiado]: ...

    @abstractmethod
    async def deuda_de_cliente(self, cliente_id: int) -> Decimal:
        """Suma de saldos pendientes del cliente (para validar el límite de crédito)."""

    @abstractmethod
    async def actualizar_saldo(self, fiado_id: int, nuevo_saldo: Decimal, estado: str) -> None: ...

    # ---- Abonos ----
    @abstractmethod
    async def crear_abono(self, abono: Abono) -> Abono: ...

    @abstractmethod
    async def abonos_de_fiado(self, fiado_id: int) -> list[Abono]: ...

    @abstractmethod
    async def abonos_de_turno(self, turno_id: int) -> list[dict]:
        """Abonos cobrados durante el turno, con el nombre del cliente (rastro)."""
