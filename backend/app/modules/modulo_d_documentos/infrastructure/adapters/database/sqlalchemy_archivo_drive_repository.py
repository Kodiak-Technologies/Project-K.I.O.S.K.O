from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_d_documentos.domain.entities import ArchivoDrive
from app.modules.modulo_d_documentos.infrastructure.adapters.database.models import ArchivoDriveModel
from app.modules.modulo_d_documentos.domain.value_objects import EstadoArchivoDrive


def _a_entidad(fila: ArchivoDriveModel) -> ArchivoDrive:
    return ArchivoDrive(
        id=fila.id,
        boleta_id=fila.boleta_id,
        archivo_nombre=fila.archivo_nombre,
        carpeta=fila.carpeta,
        estado=fila.estado,
        intentos=fila.intentos,
        drive_file_id=fila.drive_file_id,
        error_mensaje=fila.error_mensaje,
        creado_en=fila.creado_en,
        actualizado_en=fila.actualizado_en,
    )


class SqlAlchemyArchivoDriveRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def buscar_por_boleta_id(self, boleta_id: int) -> ArchivoDrive | None:
        resultado = await self._db.execute(
            select(ArchivoDriveModel).where(ArchivoDriveModel.boleta_id == boleta_id)
        )
        fila = resultado.scalar_one_or_none()
        return _a_entidad(fila) if fila else None

    async def crear(self, archivo: ArchivoDrive) -> ArchivoDrive:
        fila = ArchivoDriveModel(
            boleta_id=archivo.boleta_id,
            archivo_nombre=archivo.archivo_nombre,
            carpeta=archivo.carpeta,
            estado=archivo.estado,
        )
        self._db.add(fila)
        await self._db.flush()
        await self._db.refresh(fila)
        return _a_entidad(fila)

    async def actualizar_estado(self, archivo: ArchivoDrive) -> ArchivoDrive:
        fila = await self._db.get(ArchivoDriveModel, archivo.id)
        if fila is None:
            raise ValueError(f"ArchivoDrive {archivo.id} no existe")
        fila.estado = archivo.estado
        fila.drive_file_id = archivo.drive_file_id
        fila.intentos = archivo.intentos
        fila.error_mensaje = archivo.error_mensaje
        await self._db.flush()
        return _a_entidad(fila)

    async def listar_pendientes(self) -> list[ArchivoDrive]:
        resultado = await self._db.execute(
            select(ArchivoDriveModel)
            .where(ArchivoDriveModel.estado == EstadoArchivoDrive.PENDIENTE.value)
            .order_by(ArchivoDriveModel.creado_en)
        )
        return [_a_entidad(fila) for fila in resultado.scalars().all()]
