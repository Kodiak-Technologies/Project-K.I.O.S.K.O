import asyncio
import io
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.modules.modulo_d_documentos.domain.entities import OAuthToken
from app.modules.modulo_d_documentos.domain.ports.drive_storage_port import DriveStoragePort
from app.modules.modulo_d_documentos.domain.ports.oauth_token_port import OAuthTokenRepositoryPort
from app.shared.config.settings import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveAdapter(DriveStoragePort):
    def __init__(
        self,
        token_repository: OAuthTokenRepositoryPort | None = None,
    ) -> None:
        self.folder_id = settings.google_drive_folder_id
        self.client_id = settings.google_drive_client_id
        self.client_secret = settings.google_drive_client_secret
        self.redirect_uri = settings.google_drive_redirect_uri
        self._token_repository = token_repository

    def obtener_auth_url(self) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        query = urlencode(params)
        return f"{GOOGLE_AUTH_URL}?{query}"

    async def intercambiar_code_por_tokens(self, code: str) -> OAuthToken:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()

        token_expiry = None
        if "expires_in" in data:
            token_expiry = datetime.now(timezone.utc).replace(
                microsecond=0
            ) + timedelta(seconds=data["expires_in"])

        return OAuthToken(
            id=None,
            proveedor="google_drive",
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            token_expiry=token_expiry,
        )

    async def _obtener_credenciales(self) -> Credentials:
        if self._token_repository is None:
            raise RuntimeError("Token repository no configurado")

        token_entity = await self._token_repository.obtener_por_proveedor("google_drive")
        if token_entity is None:
            raise RuntimeError("Google Drive no está autorizado. Ejecuta GET /drive/auth-url primero.")

        token_expiry = token_entity.token_expiry
        if token_expiry is not None and token_expiry.tzinfo is not None:
            token_expiry = token_expiry.replace(tzinfo=None)

        creds = Credentials(
            token=token_entity.access_token,
            refresh_token=token_entity.refresh_token,
            token_uri=GOOGLE_TOKEN_URL,
            client_id=self.client_id,
            client_secret=self.client_secret,
            expiry=token_expiry,
        )

        if creds.expired or not creds.valid:
            await asyncio.to_thread(creds.refresh, Request())
            token_entity.access_token = creds.token
            if creds.expiry:
                token_entity.token_expiry = creds.expiry.replace(tzinfo=timezone.utc)
            await self._token_repository.actualizar(token_entity)

        return creds

    async def subir(self, archivo_bytes: bytes, nombre: str, carpeta: str) -> str:
        creds = await self._obtener_credenciales()
        service = await asyncio.to_thread(build, "drive", "v3", credentials=creds)

        folder_id = await self._asegurar_carpeta(service, carpeta)

        media = MediaIoBaseUpload(
            io.BytesIO(archivo_bytes),
            mimetype="image/png",
            resumable=True,
        )

        file_metadata = {
            "name": nombre,
            "parents": [folder_id],
        }

        file = await asyncio.to_thread(
            service.files().create(
                body=file_metadata, media_body=media, fields="id"
            ).execute
        )

        return file["id"]

    async def obtener_url(self, file_id: str) -> str:
        creds = await self._obtener_credenciales()
        service = await asyncio.to_thread(build, "drive", "v3", credentials=creds)

        file = await asyncio.to_thread(
            service.files().get(
                fileId=file_id, fields="webViewLink"
            ).execute
        )

        return file.get("webViewLink", "")

    async def _asegurar_carpeta(self, service, carpeta: str) -> str:
        partes = carpeta.split("/")
        parent_id = self.folder_id

        for parte in partes:
            query = (
                f"name='{parte}' and "
                f"'{parent_id}' in parents and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"trashed=false"
            )

            results = await asyncio.to_thread(
                service.files().list(q=query, fields="files(id)").execute
            )
            items = results.get("files", [])

            if items:
                parent_id = items[0]["id"]
            else:
                file_metadata = {
                    "name": parte,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_id],
                }
                file = await asyncio.to_thread(
                    service.files().create(
                        body=file_metadata, fields="id"
                    ).execute
                )
                parent_id = file["id"]

        return parent_id
