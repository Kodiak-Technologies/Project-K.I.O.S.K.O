import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

from app.modules.modulo_d_documentos.domain.ports.drive_storage_port import DriveStoragePort


class GoogleDriveAdapter(DriveStoragePort):
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self) -> None:
        creds_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON", "")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        self._service = None

        if not creds_json:
            return

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
            return

        self._service = build("drive", "v3", credentials=creds)

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
