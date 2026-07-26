"""Caso de uso: editar una Merma en estado Registrada.

Pre-condiciones (sdd/modulo-b-aprobaciones-detalle-editar, FR-4):
  - Estado == Registrada (si no, 409 NOT_EDITABLE_STATE).
  - Usuario es ADMIN o el creador (sino, 403 FORBIDDEN).
  - Body con al menos un campo editable (sino, 422 EMPTY_PATCH).
  - `motivo` ∈ {vencimiento, rotura, otro} (sino, 422 INVALID_MOTIVO).
  - `cantidad > 0` (sino, 422 INVALID_CANTIDAD).
"""
from __future__ import annotations

from typing import Any

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.ports.merma_repository_port import (
    MermaRepositoryPort,
)
from app.shared.kernel.exceptions import (
    NoEncontradoError,
    ValidacionError,
)


class EditarMermaUseCase:
    def __init__(
        self,
        merma_repo: MermaRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._mermas = merma_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        *,
        merma_id: int,
        editor_id: int,
        editor_nombre: str,
        es_admin: bool,
        motivo: str | None = ...,
        observacion: str | None = ...,
        proveedor_id: int | None = ...,
        producto_id: int | None = ...,
        cantidad: int | None = ...,
        ip: str = "",
        user_agent: str = "",
    ) -> Any:
        # 1. EMPTY_PATCH
        if all(
            v is ...
            for v in (motivo, observacion, proveedor_id, producto_id, cantidad)
        ):
            raise ValidacionError(
                "Debes enviar al menos un campo para editar.",
                code="EMPTY_PATCH",
            )

        # 2. FOR UPDATE lock
        merma = await self._mermas.find_by_id_for_update(merma_id)
        if merma is None:
            raise NoEncontradoError(
                "La merma no existe o fue eliminada.",
                code="MERMA_NOT_FOUND",
            )

        # 3. Entity mutation (raises NOT_EDITABLE_STATE / FORBIDDEN / INVALID_MOTIVO)
        cabecera_anterior: dict = {
            "motivo": str(merma.motivo),
            "observacion": merma.observacion,
            "proveedor_id": merma.proveedor_id,
            "producto_id": merma.producto_id,
            "cantidad": merma.cantidad,
        }
        cambios = merma.editar(
            editor_id=editor_id,
            editor_nombre=editor_nombre,
            es_admin=es_admin,
            motivo=motivo,
            observacion=observacion,
            proveedor_id=proveedor_id,
            producto_id=producto_id,
            cantidad=cantidad,
        )

        # 4. Persist cabecera
        await self._mermas.actualizar_cabecera(merma_id, cambios)

        # 5. Audit
        cabecera_nueva: dict = {
            "motivo": str(merma.motivo),
            "observacion": merma.observacion,
            "proveedor_id": merma.proveedor_id,
            "producto_id": merma.producto_id,
            "cantidad": merma.cantidad,
        }
        await self._auditoria.ejecutar(
            accion="editar_merma",
            entidad="mermas",
            usuario_id=editor_id,
            rol="",
            entidad_id=merma_id,
            motivo=(
                (observacion if observacion is not ... else None) or ""
            ),
            ip=ip,
            user_agent=user_agent,
            valor_anterior={"cabecera": cabecera_anterior},
            valor_nuevo={"cabecera": cabecera_nueva},
        )

        return merma
