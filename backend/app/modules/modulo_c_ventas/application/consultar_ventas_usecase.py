# Caso de uso: consultar ventas registradas con filtros (fecha, turno).
from datetime import date

from app.modules.modulo_c_ventas.domain.entities import Venta
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class ConsultarVentasUseCase:
    def __init__(self, venta_repo: VentaRepositoryPort):
        self._ventas = venta_repo

    async def listar(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        turno_id: int | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[Venta], int]:
        """(ventas, total). Sin `page` devuelve todo (uso interno del Módulo D)."""
        if page is not None:
            if page < 1:
                raise ValidacionError("page debe ser >= 1.")
            if page_size is None or page_size < 1 or page_size > 100:
                raise ValidacionError("page_size debe estar entre 1 y 100.")
        return await self._ventas.listar(desde, hasta, turno_id, page, page_size)

    async def obtener(self, venta_id: int) -> Venta:
        venta = await self._ventas.buscar_por_id(venta_id)
        if venta is None:
            raise NoEncontradoError("Venta no encontrada.")
        return venta
