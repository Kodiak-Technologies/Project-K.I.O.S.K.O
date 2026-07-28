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
        # Un solo INSERT con nombre + descripción + autoría (antes se insertaba
        # solo el nombre y se hacía un UPDATE extra que perdía `creado_por`).
        creada = await self._categorias.crear(
            Categoria(
                id=None,
                nombre=nombre.strip(),
                descripcion=descripcion,
                creado_por=usuario_id,
                creado_por_nombre=usuario_nombre,
            )
        )
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
