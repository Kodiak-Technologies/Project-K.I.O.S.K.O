# Caso de uso: consultar la bitácora con filtros (solo ADMIN). Solo lectura.
from datetime import datetime

from app.modules.modulo_a_seguridad.domain.entities import RegistroAuditoria
from app.modules.modulo_a_seguridad.domain.ports.auditoria_repository_port import (
    AuditoriaRepositoryPort,
)


class ConsultarBitacoraUseCase:
    def __init__(self, auditoria_repo: AuditoriaRepositoryPort):
        self._auditoria_repo = auditoria_repo

    async def ejecutar(
        self,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        usuario_id: int | None = None,
        accion: str | None = None,
        entidad: str | None = None,
        pagina: int = 1,
        tamano_pagina: int = 25,
    ) -> tuple[list[RegistroAuditoria], int]:
        return await self._auditoria_repo.consultar(
            desde=desde, hasta=hasta, usuario_id=usuario_id,
            accion=accion, entidad=entidad,
            pagina=max(1, pagina), tamano_pagina=min(max(1, tamano_pagina), 100),
        )
