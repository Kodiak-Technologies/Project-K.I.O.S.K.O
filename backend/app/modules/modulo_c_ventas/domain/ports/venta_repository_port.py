# Puerto: contrato para persistir/consultar ventas, sus detalles y sus reversos.
from abc import ABC, abstractmethod
from datetime import date

from app.modules.modulo_c_ventas.domain.entities import Anulacion, Venta


class VentaRepositoryPort(ABC):
    @abstractmethod
    async def crear(self, venta: Venta) -> Venta: ...

    @abstractmethod
    async def buscar_por_id(self, venta_id: int) -> Venta | None: ...

    @abstractmethod
    async def buscar_por_uuid(self, client_uuid: str) -> Venta | None:
        """Para la sincronización offline: reintentar no duplica (RF-26)."""

    @abstractmethod
    async def listar(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        turno_id: int | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[Venta], int]:
        """(ventas, total). Más recientes primero, con sus detalles.
        Con `page`/`page_size` la consulta se acota en SQL."""

    @abstractmethod
    async def actualizar_estado(
        self, venta_id: int, estado: str, motivo: str | None = None
    ) -> None: ...

    @abstractmethod
    async def registrar_devolucion_detalle(self, detalle_id: int, cantidad: int) -> None:
        """Acumula cantidad_devuelta en la línea de la venta."""

    @abstractmethod
    async def crear_anulacion(self, anulacion: Anulacion) -> Anulacion: ...

    @abstractmethod
    async def anulaciones_de_venta(self, venta_id: int) -> list[Anulacion]: ...

    @abstractmethod
    async def anulaciones_de_turno(self, turno_id: int) -> list[Anulacion]:
        """Reversos HECHOS durante el turno (el rastro del panel del ADMIN)."""
