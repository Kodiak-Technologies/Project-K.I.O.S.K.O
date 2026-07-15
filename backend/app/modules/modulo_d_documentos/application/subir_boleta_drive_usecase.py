from datetime import datetime, timezone

from app.modules.modulo_d_documentos.domain.entities import ArchivoDrive, Boleta
from app.modules.modulo_d_documentos.domain.ports.boleta_repository_port import BoletaRepositoryPort
from app.modules.modulo_d_documentos.domain.ports.drive_storage_port import DriveStoragePort
from app.modules.modulo_d_documentos.domain.ports.archivo_drive_repository_port import ArchivoDriveRepositoryPort
from app.modules.modulo_d_documentos.domain.value_objects import EstadoArchivoDrive
from app.shared.kernel.exceptions import NoEncontradoError


class SubirBoletaDriveUseCase:
    def __init__(
        self,
        boleta_repo: BoletaRepositoryPort,
        drive_storage: DriveStoragePort,
        archivo_drive_repo: ArchivoDriveRepositoryPort,
    ) -> None:
        self._boleta_repo = boleta_repo
        self._drive_storage = drive_storage
        self._archivo_drive_repo = archivo_drive_repo

    async def ejecutar(self, boleta_id: int) -> ArchivoDrive:
        boleta = await self._boleta_repo.buscar_por_id(boleta_id)
        if boleta is None:
            raise NoEncontradoError(f"La boleta #{boleta_id} no existe.")

        ahora = datetime.now(timezone.utc)
        nombre_archivo = f"BOL-{boleta.numero}_{ahora.strftime('%Y%m%d')}.png"
        carpeta = f"boletas/{ahora.strftime('%Y/%m')}"

        archivo = ArchivoDrive(
            id=None,
            boleta_id=boleta_id,
            archivo_nombre=nombre_archivo,
            carpeta=carpeta,
            estado=EstadoArchivoDrive.PENDIENTE.value,
        )
        archivo = await self._archivo_drive_repo.crear(archivo)

        try:
            archivo_bytes = b"simulated-png-data"
            drive_file_id = await self._drive_storage.subir(
                archivo_bytes, nombre_archivo, carpeta
            )

            archivo.estado = EstadoArchivoDrive.SUBIDO.value
            archivo.drive_file_id = drive_file_id
            archivo.intentos += 1
            archivo.actualizado_en = datetime.now(timezone.utc)
            await self._archivo_drive_repo.actualizar_estado(archivo)

            url = await self._drive_storage.obtener_url(drive_file_id)
            boleta.url_pdf = url
            await self._boleta_repo.crear(boleta)

        except Exception as e:
            archivo.estado = EstadoArchivoDrive.FALLIDO.value
            archivo.error_mensaje = str(e)
            archivo.intentos += 1
            archivo.actualizado_en = datetime.now(timezone.utc)
            await self._archivo_drive_repo.actualizar_estado(archivo)

        return archivo
