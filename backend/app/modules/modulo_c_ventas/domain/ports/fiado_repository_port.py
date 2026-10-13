# Puerto: cuentas de fiado (clientes, su saldo y su estado de cuenta).
from abc import ABC, abstractmethod
from decimal import Decimal

from app.modules.modulo_c_ventas.domain.entities import ClienteFiado, MovimientoFiado


class FiadoRepositoryPort(ABC):
    @abstractmethod
    async def listar_clientes(self, buscar: str | None = None, incluir_inactivos: bool = False) -> list[ClienteFiado]:
        """Clientes con su saldo y lo fiado en el mes actual."""

    @abstractmethod
    async def buscar_cliente(self, cliente_id: int) -> ClienteFiado | None: ...

    @abstractmethod
    async def existe_nombre(self, nombre: str, excepto_id: int | None = None) -> bool: ...

    @abstractmethod
    async def crear_cliente(self, cliente: ClienteFiado, usuario_id: int) -> ClienteFiado: ...

    @abstractmethod
    async def actualizar_cliente(self, cliente_id: int, cambios: dict) -> ClienteFiado: ...

    @abstractmethod
    async def registrar_movimiento(self, movimiento: MovimientoFiado, delta_saldo: Decimal) -> MovimientoFiado:
        """Aplica `delta_saldo` al cliente y guarda el movimiento con el saldo
        resultante, en una sola sentencia (atómico ante dos cajas a la vez)."""

    @abstractmethod
    async def movimientos_de_cliente(self, cliente_id: int, limite: int = 200) -> list[MovimientoFiado]: ...

    @abstractmethod
    async def cobros_de_turno(self, turno_id: int) -> list[MovimientoFiado]:
        """Pagos y adelantos que entraron a la caja de ESE turno."""

    @abstractmethod
    async def fiado_pendiente_de_venta(self, venta_id: int) -> tuple[int | None, Decimal]:
        """(cliente_id, monto fiado de la venta que aún no se revirtió)."""

    @abstractmethod
    async def clientes_por_venta(self, venta_ids: list[int]) -> dict[int, str]:
        """{venta_id: nombre del cliente} de las ventas fiadas."""

    @abstractmethod
    async def fiado_revertido_por_anulacion(self, anulacion_ids: list[int]) -> dict[int, Decimal]: ...
