# Caso de uso: listar pagos de un proveedor (CU-B12b, REQ-LP).
# Devuelve además la deuda_actual del proveedor.
from app.modules.modulo_b_inventario.domain.entities import PagoProveedor
from app.modules.modulo_b_inventario.domain.ports.pago_proveedor_repository_port import (
    PagoProveedorRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class ListarPagosProveedorUseCase:
    def __init__(
        self,
        pago_repo: PagoProveedorRepositoryPort,
        proveedor_repo: ProveedorRepositoryPort,
    ):
        self._pagos = pago_repo
        self._proveedores = proveedor_repo

    async def ejecutar(
        self,
        proveedor_id: int,
        *,
        tipo: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PagoProveedor], int, "object", int, int, int]:
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        prov = await self._proveedores.find_by_id(proveedor_id)
        if prov is None:
            raise NoEncontradoError("El proveedor no existe.")
        items, total = await self._pagos.listar_por_proveedor(
            proveedor_id,
            tipo=tipo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return items, total, prov.deuda_actual, page, page_size, total_pages
