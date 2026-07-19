from typing import Protocol


class DriveStoragePort(Protocol):
    async def subir(
        self, archivo_bytes: bytes, nombre: str, carpeta: str
    ) -> str:
        """Sube un archivo y retorna el URL o file_id del archivo subido."""
        ...

    async def obtener_url(self, file_id: str) -> str:
        """Retorna el URL de descarga de un archivo por su file_id."""
        ...
