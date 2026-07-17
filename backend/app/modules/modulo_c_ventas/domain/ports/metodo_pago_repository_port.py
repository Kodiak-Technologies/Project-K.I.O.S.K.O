# Puerto: contrato para el catálogo de métodos de pago (el ADMIN lo gestiona, RF-20).
from abc import ABC, abstractmethod

from app.modules.modulo_c_ventas.domain.entities import MetodoPago


class MetodoPagoRepositoryPort(ABC):
    @abstractmethod
    async def listar(self, solo_activos: bool = True) -> list[MetodoPago]: ...

    @abstractmethod
    async def buscar_por_codigo(self, codigo: str) -> MetodoPago | None: ...

    @abstractmethod
    async def crear(self, metodo: MetodoPago) -> MetodoPago: ...

    @abstractmethod
    async def actualizar(self, metodo_id: int, cambios: dict) -> MetodoPago: ...
