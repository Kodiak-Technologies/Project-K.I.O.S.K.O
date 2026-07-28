# Adaptador: implementa PermisoRepositoryPort usando SQLAlchemy async.
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import Permiso, Rol
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    PermisoModel,
    RolModel,
    RolPermisoModel,
)
from app.shared.kernel.exceptions import ValidacionError


class SqlAlchemyPermisoRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def listar_roles(self) -> list[Rol]:
        filas = (await self._db.execute(select(RolModel).order_by(RolModel.id))).scalars().all()
        return [Rol(id=f.id, nombre=f.nombre, descripcion=f.descripcion) for f in filas]

    async def listar_permisos(self) -> list[Permiso]:
        filas = (await self._db.execute(select(PermisoModel).order_by(PermisoModel.codigo))).scalars().all()
        return [Permiso(id=f.id, codigo=f.codigo, descripcion=f.descripcion) for f in filas]

    async def permisos_de_rol(self, rol_id: int) -> list[Permiso]:
        filas = (
            await self._db.execute(
                select(PermisoModel)
                .join(RolPermisoModel, RolPermisoModel.permiso_id == PermisoModel.id)
                .where(RolPermisoModel.rol_id == rol_id)
                .order_by(PermisoModel.codigo)
            )
        ).scalars().all()
        return [Permiso(id=f.id, codigo=f.codigo, descripcion=f.descripcion) for f in filas]

    async def rol_tiene_permiso(self, rol_id: int, codigo_permiso: str) -> bool:
        fila = (
            await self._db.execute(
                select(RolPermisoModel.permiso_id)
                .join(PermisoModel, PermisoModel.id == RolPermisoModel.permiso_id)
                .where(RolPermisoModel.rol_id == rol_id, PermisoModel.codigo == codigo_permiso)
            )
        ).first()
        return fila is not None

    async def reemplazar_permisos_de_rol(self, rol_id: int, codigos: list[str]) -> list[Permiso]:
        permisos = (
            await self._db.execute(select(PermisoModel).where(PermisoModel.codigo.in_(codigos)))
        ).scalars().all()
        encontrados = {p.codigo for p in permisos}
        desconocidos = set(codigos) - encontrados
        if desconocidos:
            raise ValidacionError(f"Permisos inexistentes: {', '.join(sorted(desconocidos))}")

        await self._db.execute(delete(RolPermisoModel).where(RolPermisoModel.rol_id == rol_id))
        for permiso in permisos:
            self._db.add(RolPermisoModel(rol_id=rol_id, permiso_id=permiso.id))
        await self._db.flush()
        return await self.permisos_de_rol(rol_id)
