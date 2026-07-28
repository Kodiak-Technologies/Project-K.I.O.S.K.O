# Adaptador: implementa UsuarioRepositoryPort usando SQLAlchemy async.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    RolModel,
    UsuarioModel,
)


def _a_entidad(fila: UsuarioModel, rol_nombre: str) -> Usuario:
    return Usuario(
        id=fila.id,
        username=fila.username,
        nombre=fila.nombre,
        password_hash=fila.password_hash,
        rol_id=fila.rol_id,
        rol_nombre=rol_nombre,
        activo=fila.activo,
        debe_cambiar_password=fila.debe_cambiar_password,
        intentos_fallidos=fila.intentos_fallidos,
        bloqueado_hasta=fila.bloqueado_hasta,
        ultimo_acceso=fila.ultimo_acceso,
        created_at=fila.created_at,
        updated_at=fila.updated_at,
        deleted_at=fila.deleted_at,
        deleted_by=fila.deleted_by,
    )


class SqlAlchemyUsuarioRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        resultado = await self._db.execute(
            select(UsuarioModel, RolModel.nombre)
            .join(RolModel, UsuarioModel.rol_id == RolModel.id)
            .where(UsuarioModel.id == usuario_id)
        )
        fila = resultado.first()
        return _a_entidad(fila[0], fila[1]) if fila else None

    async def buscar_por_username(self, username: str) -> Usuario | None:
        resultado = await self._db.execute(
            select(UsuarioModel, RolModel.nombre)
            .join(RolModel, UsuarioModel.rol_id == RolModel.id)
            .where(UsuarioModel.username == username)
        )
        fila = resultado.first()
        return _a_entidad(fila[0], fila[1]) if fila else None

    async def listar(self, incluir_eliminados: bool = False) -> list[Usuario]:
        consulta = (
            select(UsuarioModel, RolModel.nombre)
            .join(RolModel, UsuarioModel.rol_id == RolModel.id)
            .order_by(UsuarioModel.id)
        )
        if not incluir_eliminados:
            consulta = consulta.where(UsuarioModel.deleted_at.is_(None))
        resultado = await self._db.execute(consulta)
        return [_a_entidad(fila[0], fila[1]) for fila in resultado.all()]

    async def crear(self, usuario: Usuario) -> Usuario:
        fila = UsuarioModel(
            username=usuario.username,
            nombre=usuario.nombre,
            password_hash=usuario.password_hash,
            rol_id=usuario.rol_id,
            activo=usuario.activo,
            debe_cambiar_password=usuario.debe_cambiar_password,
        )
        self._db.add(fila)
        await self._db.flush()
        return await self.buscar_por_id(fila.id)  # type: ignore[return-value]

    async def actualizar(self, usuario: Usuario) -> Usuario:
        fila = await self._db.get(UsuarioModel, usuario.id)
        if fila is None:
            raise ValueError(f"Usuario {usuario.id} no existe")
        fila.nombre = usuario.nombre
        fila.password_hash = usuario.password_hash
        fila.rol_id = usuario.rol_id
        fila.activo = usuario.activo
        fila.debe_cambiar_password = usuario.debe_cambiar_password
        fila.intentos_fallidos = usuario.intentos_fallidos
        fila.bloqueado_hasta = usuario.bloqueado_hasta
        fila.ultimo_acceso = usuario.ultimo_acceso
        fila.deleted_at = usuario.deleted_at
        fila.deleted_by = usuario.deleted_by
        await self._db.flush()
        return await self.buscar_por_id(fila.id)  # type: ignore[return-value]
