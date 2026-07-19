# Caso de uso: editar una categoría (derivado del scope del Módulo B).
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Categoria
from app.modules.modulo_b_inventario.domain.ports.categoria_repository_port import (
    CategoriaRepositoryPort,
)


class EditarCategoriaUseCase:
    def __init__(
        self,
        categoria_repo: CategoriaRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._categorias = categoria_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        categoria_id: int,
        cambios: dict,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Categoria:
        anterior = await self._categorias.find_by_id(categoria_id)
        actualizada = await self._categorias.actualizar(
            categoria_id, cambios, usuario_id=usuario_id, usuario_nombre=usuario_nombre
        )
        await self._auditoria.ejecutar(
            accion="categoria_editada",
            entidad="categorias",
            usuario_id=usuario_id,
            rol="",
            entidad_id=categoria_id,
            valor_anterior={
                "nombre": anterior.nombre if anterior else None,
                "descripcion": anterior.descripcion if anterior else None,
            } if anterior else None,
            valor_nuevo={
                k: v for k, v in cambios.items() if v is not None
            },
            ip=ip,
            user_agent=user_agent,
        )
        return actualizada
