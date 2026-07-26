# Puerto: contrato para registrar y consultar la bitácora de auditoría.
# La bitácora es INMUTABLE: por eso el puerto no ofrece actualizar ni borrar.
from datetime import datetime
from typing import Protocol

from app.modules.modulo_a_seguridad.domain.entities import RegistroAuditoria


class AuditoriaRepositoryPort(Protocol):
    async def registrar(self, registro: RegistroAuditoria) -> RegistroAuditoria: ...

    async def consultar(
        self,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        usuario_id: int | None = None,
        accion: str | None = None,
        entidad: str | None = None,
        pagina: int = 1,
        tamano_pagina: int = 25,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[RegistroAuditoria], int]:
        """Devuelve (registros de la página, total de registros que cumplen el filtro).

        Con `cursor` pagina por keyset —"lo que viene después de esa fila"— y
        `pagina` se ignora. Es lo que corresponde acá: la bitácora recibe filas
        nuevas por arriba continuamente, y con OFFSET eso corre las páginas y
        hace que se repitan o se salteen registros.
        """
        ...
