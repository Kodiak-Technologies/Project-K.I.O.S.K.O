# Puerto: contrato para subir la foto de boleta de una solicitud de ingreso.
# El adaptador de producción es `drive_storage_adapter.py` (Google Drive).
from abc import ABC, abstractmethod
from typing import Literal

from app.modules.modulo_b_inventario.domain.value_objects import StorageResult


class StoragePort(ABC):
    """Puerto de subida de archivos.

    Configuración en runtime (ver `settings.py`): las credenciales OAuth de
    Google Drive y `GOOGLE_DRIVE_FOLDER_ID`, las mismas que usan los respaldos
    del Módulo D.
    """

    @abstractmethod
    async def subir(
        self,
        carpeta: Literal["boletas"],
        filename: str,
        content: bytes,
        mime: str,
    ) -> StorageResult:
        """Sube el archivo y devuelve su URL pública permanente y su id.

        La URL queda accesible para cualquiera que tenga el enlace: el `<img>`
        del navegador no manda credenciales de Google y si no recibiría 403.
        """
