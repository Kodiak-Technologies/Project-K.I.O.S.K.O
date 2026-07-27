"""Listar respaldos .sql en Google Drive."""

import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _parsear_database_url(url: str) -> dict:
    raw = url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    partes = raw.split("@")
    auth = partes[0].split(":")
    host_db = partes[1].split("/")
    user, password = auth[0], auth[1]
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    dbname = host_db[1]
    return {"host": host, "port": port, "user": user, "password": password, "dbname": dbname}


async def main():
    database_url = os.environ.get("DATABASE_URL", "")
    db_params = _parsear_database_url(database_url)
    conn = await asyncpg.connect(
        host=db_params["host"], port=db_params["port"],
        user=db_params["user"], password=db_params["password"],
        database=db_params["dbname"], statement_cache_size=0,
    )
    try:
        fila = await conn.fetchrow(
            "SELECT access_token, refresh_token, token_expiry "
            "FROM oauth_tokens WHERE proveedor = 'google_drive' LIMIT 1"
        )
        if not fila:
            print("No hay tokens"); return
        expiry = fila["token_expiry"]
        if expiry and expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
        creds = Credentials(
            token=fila["access_token"], refresh_token=fila["refresh_token"],
            token_uri=GOOGLE_TOKEN_URL,
            client_id=os.environ.get("GOOGLE_DRIVE_CLIENT_ID", ""),
            client_secret=os.environ.get("GOOGLE_DRIVE_CLIENT_SECRET", ""),
            expiry=expiry,
        )
        if creds.expired or not creds.valid:
            creds.refresh(Request())
        service = await asyncio.to_thread(build, "drive", "v3", credentials=creds)
        results = await asyncio.to_thread(
            service.files().list(
                q="name contains '.sql' and trashed=false",
                fields="files(id, name, size, createdTime)",
                orderBy="name asc",
            ).execute
        )
        files = results.get("files", [])
        print(f"Archivos .sql en Drive ({len(files)}):\n")
        for f in files:
            size_mb = int(f.get("size", 0)) / (1024 * 1024)
            print(f"  {f['name']}  ({size_mb:.1f} MB, {f.get('createdTime', '?')})")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
