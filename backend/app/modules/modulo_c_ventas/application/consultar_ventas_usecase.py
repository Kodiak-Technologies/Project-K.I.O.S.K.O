# Caso de uso: consultar ventas registradas con filtros (fecha, turno).
from datetime import date

from app.modules.modulo_c_ventas.domain.entities import Venta
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.shared.kernel.exceptions import NoEncontradoError


class ConsultarVentasUseCase:
    def __init__(self, venta_repo: VentaRepositoryPort):
        self._ventas = venta_repo

    async def listar(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        turno_id: int | None = None,
    ) -> list[Venta]:
        return await self._ventas.listar(desde, hasta, turno_id)

    async def obtener(self, venta_id: int) -> Venta:
        venta = await self._ventas.buscar_por_id(venta_id)
        if venta is None:
            raise NoEncontradoError("Venta no encontrada.")
        return venta
