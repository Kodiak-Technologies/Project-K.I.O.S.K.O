"""Adaptador de `StoragePort` contra Google Drive.

Las boletas de ingreso van al mismo Drive que los respaldos del Módulo D
(`GOOGLE_DRIVE_FOLDER_ID`). Es el único destino: no hay otro backend de storage.

Dos cosas que conviene tener presentes:

1. **El archivo queda público.** El frontend muestra la boleta con
   `<img src=...>`, y el navegador no manda el token de la API ni credenciales
   de Google. Para que la imagen cargue hay que darle permiso de lectura a
   "cualquiera con el enlace". Es una decisión tomada a conciencia: quien tenga
   el link ve la boleta sin estar logueado. La alternativa era servirla por un
   endpoint propio (privada, pero más código).

2. **La URL no vence.** El `file_id` de Drive es permanente, así que el enlace
   que se guarda en `solicitudes_ingreso.foto_boleta_url` sirve para siempre.

Sobre el formato de URL: se usa `lh3.googleusercontent.com/d/{file_id}`, pero
no hay que confiar en que ése cargue. Cuál de los formatos de Google sirve la
imagen fue cambiando, así que el frontend (`ImagenConRespaldo`) prueba varios y,
si fallan todos, pide el archivo a `GET /storage/boleta/{file_id}`, que lo lee
de Drive con estas mismas credenciales y no depende de que sea público.
"""

from __future__ import annotations

import asyncio

from googleapiclient.discovery import build

from app.modules.modulo_b_inventario.domain.ports.storage_port import StoragePort
from app.modules.modulo_b_inventario.domain.value_objects import StorageResult
from app.modules.modulo_d_documentos.domain.ports.drive_storage_port import (
    DriveStoragePort,
)
from app.shared.kernel.exceptions import ValidacionError

# Estructura dentro del Drive configurado (cuelga de GOOGLE_DRIVE_FOLDER_ID):
#
#   boletas/
#     ingresos/   <- fotos de boleta de las solicitudes de ingreso (esto)
#     ventas/     <- notas de venta subidas a mano
#   respaldos/    <- volcados de la BD (Módulo D)
CARPETA_BOLETAS = "boletas"
CARPETA_DRIVE_INGRESOS = "boletas/ingresos"


def url_publica(file_id: str) -> str:
    """URL que un `<img>` puede cargar directamente en el navegador sin bloqueos CORP."""
    return f"https://lh3.googleusercontent.com/d/{file_id}"


class DriveStorageAdapter(StoragePort):
    """Sube las boletas al Drive del negocio y devuelve un enlace directo."""

    def __init__(self, drive: DriveStoragePort):
        self._drive = drive

    async def subir(
        self,
        carpeta: str,
        filename: str,
        content: bytes,
        mime: str,
    ) -> StorageResult:
        if carpeta != CARPETA_BOLETAS:
            raise ValidacionError(
                f"Carpeta inválida. Sólo se permite '{CARPETA_BOLETAS}'."
            )
        # El caso de uso arma `filename` como "boletas/2026-07-27-abc.png". En
        # Drive la carpeta es un objeto aparte, no parte del nombre: si se
        # pasara entero, el archivo quedaría *llamado* "boletas/...png" y
        # colgando de la raíz. Se separa: el nombre es sólo la última parte.
        nombre_archivo = filename.rsplit("/", 1)[-1]
        try:
            file_id = await self._drive.subir(
                content, nombre_archivo, CARPETA_DRIVE_INGRESOS
            )
            await self._hacer_publico(file_id)
        except ValidacionError:
            raise
        except Exception as exc:  # noqa: BLE001
            # Drive usa OAuth: si el token se revocó o nunca se autorizó, esto
            # falla. Sin foto no se puede registrar el ingreso (HU-B06), así
            # que el mensaje tiene que decir qué hacer.
            raise ValidacionError(
                "No se pudo subir la boleta a Google Drive. Verifica que la "
                "cuenta siga autorizada en Configuración → Drive."
            ) from exc

        return StorageResult(
            url=url_publica(file_id),
            # El `path` es el file_id: es lo que identifica al archivo en Drive.
            path=file_id,
            filename=filename,
            mime=mime,
            size_bytes=len(content),
        )

    async def _hacer_publico(self, file_id: str) -> None:
        """Permiso de lectura para cualquiera con el enlace.

        Sin esto el `<img>` del navegador recibe 403: el archivo nace privado
        de la cuenta que autorizó Drive.
        """
        creds = await self._drive._obtener_credenciales()  # noqa: SLF001
        service = await asyncio.to_thread(build, "drive", "v3", credentials=creds)
        await asyncio.to_thread(
            service.permissions()
            .create(fileId=file_id, body={"role": "reader", "type": "anyone"})
            .execute
        )
