# Puerto: contrato para persistir y consultar solicitudes de ingreso de mercadería (RF-05, RF-06).
# El stock NO se toca al crear/consultar; solo al aprobar (HU-B07, D-09).
from abc import ABC, abstractmethod

from app.modules.modulo_b_inventario.domain.entities import SolicitudIngreso


class SolicitudIngresoRepositoryPort(ABC):
    @abstractmethod
    async def crear(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        """Inserta la solicitud en estado 'Pendiente' (NO toca stock)."""

    @abstractmethod
    async def find_by_id(self, solicitud_id: int) -> SolicitudIngreso | None: ...

    @abstractmethod
    async def find_by_id_for_update(self, solicitud_id: int) -> SolicitudIngreso | None:
        """SELECT ... FOR UPDATE; se usa en aprobar/rechazar para evitar race conditions."""

    @abstractmethod
    async def actualizar(self, solicitud: SolicitudIngreso) -> SolicitudIngreso:
        """Persiste cambios de estado y snapshots del revisor."""

    @abstractmethod
    async def actualizar_cabecera(
        self, solicitud_id: int, cambios: dict
    ) -> SolicitudIngreso:
        """sdd/modulo-b-aprobaciones-detalle-editar: PATCH parcial sobre la
        cabecera (proveedor, motivo, foto, audit triple). NO toca lineas.
        Devuelve la entidad refrescada."""

    @abstractmethod
    async def listar_paginado(
        self,
        *,
        estado: str | None = None,
        proveedor_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SolicitudIngreso], int]:
        """Devuelve (items, total). Filtros opcionales."""

    @abstractmethod
    async def listar_por_solicitante(
        self,
        usuario_id: int,
        *,
        estado: str | None = None,
        proveedor_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SolicitudIngreso], int]:
        """Lista las solicitudes creadas por un usuario específico (CAJERO),
        aplicando los mismos filtros que el listado general."""
