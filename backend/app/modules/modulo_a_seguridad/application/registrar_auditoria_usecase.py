# Caso de uso: registrar un evento en la bitácora. ESTE es el servicio que los
# módulos B, C y D invocan para dejar constancia de sus operaciones
# (ver docs/API_MODULO_A.md, sección "Guía de integración").
from typing import Any

from app.modules.modulo_a_seguridad.domain.entities import RegistroAuditoria
from app.modules.modulo_a_seguridad.domain.ports.auditoria_repository_port import (
    AuditoriaRepositoryPort,
)


class RegistrarAuditoriaUseCase:
    def __init__(self, auditoria_repo: AuditoriaRepositoryPort):
        self._auditoria_repo = auditoria_repo

    async def ejecutar(
        self,
        accion: str,
        entidad: str,
        usuario_id: int | None = None,
        rol: str = "",
        entidad_id: str | int | None = None,
        valor_anterior: dict[str, Any] | None = None,
        valor_nuevo: dict[str, Any] | None = None,
        motivo: str | None = None,
        ip: str = "",
        user_agent: str = "",
    ) -> RegistroAuditoria:
        return await self._auditoria_repo.registrar(
            RegistroAuditoria(
                id=None,
                usuario_id=usuario_id,
                rol=rol,
                accion=accion,
                entidad=entidad,
                entidad_id=str(entidad_id) if entidad_id is not None else None,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
                motivo=motivo,
                ip=ip,
                user_agent=user_agent,
            )
        )
