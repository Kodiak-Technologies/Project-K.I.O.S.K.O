from typing import Protocol


class DriveStoragePort(Protocol):
    async def subir(
        self, archivo_bytes: bytes, nombre: str, carpeta: str
    ) -> str:
        """Sube un archivo y retorna el file_id del archivo subido."""
        ...

    async def descargar(self, file_id: str) -> bytes:
        """Descarga un archivo por su file_id y retorna el contenido en bytes."""
        ...

    async def eliminar(self, file_id: str) -> None:
        """Elimina un archivo de Drive por su file_id."""
        ...

    async def obtener_url(self, file_id: str) -> str:
        """Retorna el URL de visualización de un archivo por su file_id."""
        ...
