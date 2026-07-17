import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

from app.modules.modulo_d_documentos.domain.ports.drive_storage_port import DriveStoragePort
from app.shared.config.settings import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent


class GoogleDriveAdapter(DriveStoragePort):
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self) -> None:
        creds_json = settings.google_drive_credentials_json
        self.folder_id = settings.google_drive_folder_id
        self._service = None

        if not creds_json:
            print("[GoogleDriveAdapter] GOOGLE_DRIVE_CREDENTIALS_JSON no configurado")
            return

        if not os.path.isabs(creds_json):
            creds_json = str(BACKEND_DIR / creds_json)

        try:
            if creds_json.strip().startswith("{"):
                creds_info = json.loads(creds_json)
                creds = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=self.SCOPES
                )
            elif os.path.exists(creds_json):
                creds = service_account.Credentials.from_service_account_file(
                    creds_json, scopes=self.SCOPES
                )
            else:
                print(f"[GoogleDriveAdapter] Archivo de credenciales no encontrado: {creds_json}")
                return

            self._service = build("drive", "v3", credentials=creds)
            print("[GoogleDriveAdapter] Servicio de Google Drive inicializado correctamente")
        except Exception as e:
            print(f"[GoogleDriveAdapter] Error al inicializar: {e}")
            self._service = None

    async def subir(self, archivo_bytes: bytes, nombre: str, carpeta: str) -> str:
        if self._service is None:
            raise RuntimeError("Google Drive no está configurado")

        folder_id = await self._asegurar_carpeta(carpeta)

        media = MediaIoBaseUpload(
            __import__("io").BytesIO(archivo_bytes),
            mimetype="image/png",
            resumable=True,
        )

        file_metadata = {
            "name": nombre,
            "parents": [folder_id],
        }

        file = self._service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()

        return file["id"]

    async def obtener_url(self, file_id: str) -> str:
        if self._service is None:
            raise RuntimeError("Google Drive no está configurado")

        file = self._service.files().get(
            fileId=file_id, fields="webViewLink"
        ).execute()

        return file.get("webViewLink", "")

    async def _asegurar_carpeta(self, carpeta: str) -> str:
        nombre_carpeta = carpeta.split("/")[-1]
        query = (
            f"name='{nombre_carpeta}' and "
            f"'{self.folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )

        results = self._service.files().list(q=query, fields="files(id)").execute()
        items = results.get("files", [])

        if items:
            return items[0]["id"]

        file_metadata = {
            "name": nombre_carpeta,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [self.folder_id],
        }

        file = self._service.files().create(
            body=file_metadata, fields="id"
        ).execute()

        return file["id"]
