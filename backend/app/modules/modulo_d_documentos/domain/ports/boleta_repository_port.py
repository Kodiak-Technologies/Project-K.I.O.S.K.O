from typing import Protocol

from app.modules.modulo_d_documentos.domain.entities import Boleta


class BoletaRepositoryPort(Protocol):
    async def buscar_por_id(self, boleta_id: int) -> Boleta | None: ...

    async def buscar_por_venta_id(self, venta_id: int) -> Boleta | None: ...

    async def listar(
        self, desde: str | None = None, hasta: str | None = None, q: str | None = None
    ) -> list[Boleta]: ...

    async def crear(self, boleta: Boleta) -> Boleta: ...

    async def actualizar(self, boleta: Boleta) -> Boleta: ...

    async def generar_siguiente_numero(self) -> str:
        """Genera el siguiente correlativo: B001-000001, B001-000002, etc."""
        ...
