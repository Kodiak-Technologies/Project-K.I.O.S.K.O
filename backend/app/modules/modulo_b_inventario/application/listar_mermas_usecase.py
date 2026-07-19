# Caso de uso: listar mermas con filtros (REQ-MER-LIST).
from app.modules.modulo_b_inventario.domain.entities import Merma
from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
    MermaRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError


class ListarMermasUseCase:
    def __init__(self, merma_repo: MermaRepositoryPort):
        self._mermas = merma_repo

    async def ejecutar(
        self,
        *,
        estado: str | None = None,
        motivo: str | None = None,
        producto_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Merma], int, int, int, int]:
        if page < 1:
            raise ValidacionError("page debe ser >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValidacionError("page_size debe estar entre 1 y 100.")
        items, total = await self._mermas.listar_paginado(
            estado=estado,
            motivo=motivo,
            producto_id=producto_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return items, total, page, page_size, total_pages
