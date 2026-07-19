# Caso de uso: crear una categoría (derivado del scope del Módulo B).
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import Categoria
from app.modules.modulo_b_inventario.domain.ports.categoria_repository_port import (
    CategoriaRepositoryPort,
)


class CrearCategoriaUseCase:
    def __init__(
        self,
        categoria_repo: CategoriaRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._categorias = categoria_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        nombre: str,
        descripcion: str | None,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> Categoria:
        # El repo valida unicidad y longitud en `crear`. La validación de longitud
        # ya la hace el Pydantic, pero la hacemos defensiva acá también.
        creada = await self._categorias.crear(nombre.strip())
        if descripcion is not None:
            await self._categorias.actualizar(
                creada.id,  # type: ignore[arg-type]
                {"descripcion": descripcion},
                usuario_id=usuario_id,
                usuario_nombre=usuario_nombre,
            )
            creada = await self._categorias.find_by_id(creada.id)  # type: ignore[arg-type]
        await self._auditoria.ejecutar(
            accion="categoria_creada",
            entidad="categorias",
            usuario_id=usuario_id,
            rol="",
            entidad_id=creada.id,  # type: ignore[arg-type]
            valor_nuevo={"nombre": creada.nombre, "descripcion": creada.descripcion},
            ip=ip,
            user_agent=user_agent,
        )
        return creada  # type: ignore[return-value]
