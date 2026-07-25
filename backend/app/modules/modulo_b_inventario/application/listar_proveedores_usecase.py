# Caso de uso: listar proveedores paginado con filtros (HU-B14).
from app.modules.modulo_b_inventario.domain.entities import Proveedor
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


class ListarProveedoresUseCase:
    def __init__(self, proveedor_repo: ProveedorRepositoryPort):
        self._proveedores = proveedor_repo

    async def ejecutar(
        self,
        *,
        search: str | None = None,
        solo_con_deuda: bool = False,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Proveedor], int, int, int, int]:
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        items, total = await self._proveedores.listar_paginado(
            search=search,
            solo_con_deuda=solo_con_deuda,
            activo=activo,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return items, total, page, page_size, total_pages
