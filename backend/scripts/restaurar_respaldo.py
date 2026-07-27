"""Restaurar un respaldo desde Google Drive.

Uso:
    python -m scripts.restaurar_respaldo

Requiere las variables de entorno en .env:
    DATABASE_URL, GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET
"""

import asyncio
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

TABLAS_ORDEN = [
    "roles", "permisos", "rol_permisos", "usuarios", "sesiones",
    "bitacora_auditoria", "configuracion_negocio",
    "categorias", "proveedores", "productos", "solicitudes_ingreso",
    "detalle_solicitud", "pagos_proveedor", "movimientos_inventario",
    "historial_precios",
    "metodos_pago", "turnos_caja", "arqueos", "ventas", "detalles_venta",
    "pagos_venta", "anulaciones",
    "notificaciones", "config_notificaciones", "respaldos", "oauth_tokens",
]


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


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------

async def _obtener_credenciales_drive(conn: asyncpg.Connection) -> Credentials:
    """Obtiene credenciales OAuth de Drive desde la BD y las refresca si es necesario."""
    client_id = os.environ.get("GOOGLE_DRIVE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_DRIVE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_DRIVE_CLIENT_ID o GOOGLE_DRIVE_CLIENT_SECRET no configurados en .env")

    fila = await conn.fetchrow(
        "SELECT access_token, refresh_token, token_expiry "
        "FROM oauth_tokens WHERE proveedor = 'google_drive' LIMIT 1"
    )
    if fila is None:
        raise RuntimeError("No hay tokens de Google Drive en la BD. Ejecuta GET /drive/auth-url primero.")

    expiry = fila["token_expiry"]
    if expiry is not None and expiry.tzinfo is not None:
        expiry = expiry.replace(tzinfo=None)

    creds = Credentials(
        token=fila["access_token"],
        refresh_token=fila["refresh_token"],
        token_uri=GOOGLE_TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        expiry=expiry,
    )

    if creds.expired or not creds.valid:
        print("  Refrescando token de Drive...")
        await asyncio.to_thread(creds.refresh, Request())
        await conn.execute(
            "UPDATE oauth_tokens SET access_token = $1, token_expiry = $2 "
            "WHERE proveedor = 'google_drive'",
            creds.token,
            creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None,
        )

    return creds


async def _listar_respaldos_drive(service) -> list[dict]:
    """Lista todos los archivos .sql en Drive (busca en subcarpetas como respaldos/2026/07/)."""
    query = (
        f"name contains '.sql' and "
        f"trashed=false"
    )
    results = await asyncio.to_thread(
        service.files().list(
            q=query,
            fields="files(id, name, size, createdTime)",
            orderBy="name desc",
        ).execute
    )
    return results.get("files", [])


async def _descargar_archivo(service, file_id: str) -> bytes:
    """Descarga un archivo de Drive por su ID."""
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = await asyncio.to_thread(downloader.next_chunk)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

async def _restaurar(sql_content: str, conn: asyncpg.Connection) -> None:
    """Ejecuta el restore completo dentro de una transacción."""
    await conn.execute("BEGIN")

    try:
        print("  Deshabilitando triggers de inmutabilidad...")
        await conn.execute("ALTER TABLE bitacora_auditoria DISABLE TRIGGER trg_bitacora_inmutable")
        await conn.execute("ALTER TABLE historial_precios DISABLE TRIGGER trg_historial_precios_no_update")

        print("  Limpiando FK autorreferencial...")
        await conn.execute("UPDATE usuarios SET deleted_by = NULL WHERE deleted_by IS NOT NULL")

        print("  Eliminando datos (orden inverso FK)...")
        tablas_bd = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        nombres_bd = {t["tablename"] for t in tablas_bd}
        tablas_a_borrar = [t for t in TABLAS_ORDEN if t in nombres_bd]
        tablas_a_borrar.extend(sorted(nombres_bd - set(tablas_a_borrar)))
        for tabla in reversed(tablas_a_borrar):
            if tabla == "respaldos":
                continue
            await conn.execute(f'DELETE FROM "{tabla}"')

        print("  Insertando datos del respaldo...")
        lineas_ejecutadas = 0
        for linea in sql_content.split("\n"):
            linea = linea.strip()
            if not linea or linea.startswith("--"):
                continue
            if linea.upper().startswith("DELETE FROM"):
                continue
            await conn.execute(linea)
            lineas_ejecutadas += 1

        print("  Restableciendo secuencias...")
        # Los SETVAL ya vienen en el archivo, se ejecutan con el loop anterior

        await conn.execute("COMMIT")
        print(f"  Transacción confirmada ({lineas_ejecutadas} sentencias ejecutadas).")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        print("  Revirtiendo cambios (ROLLBACK)...")
        await conn.execute("ROLLBACK")
        raise

    finally:
        print("  Habilitando triggers...")
        try:
            await conn.execute("ALTER TABLE bitacora_auditoria ENABLE TRIGGER trg_bitacora_inmutable")
            await conn.execute("ALTER TABLE historial_precios ENABLE TRIGGER trg_historial_precios_no_update")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL no configurada en .env")
        sys.exit(1)

    db_params = _parsear_database_url(database_url)
    conn = await asyncpg.connect(
        host=db_params["host"],
        port=db_params["port"],
        user=db_params["user"],
        password=db_params["password"],
        database=db_params["dbname"],
        statement_cache_size=0,
    )

    try:
        print("\n=== Restaurar respaldo desde Google Drive ===\n")

        # 1. Conectar a Drive
        print("Conectando a Google Drive...")
        creds = await _obtener_credenciales_drive(conn)
        service = await asyncio.to_thread(build, "drive", "v3", credentials=creds)

        # 2. Listar archivos
        print("Buscando respaldos disponibles...")
        archivos = await _listar_respaldos_drive(service)

        if not archivos:
            print("No se encontraron archivos .sql en la carpeta de respaldos de Drive.")
            return

        print(f"\nArchivos disponibles ({len(archivos)}):\n")
        for i, archivo in enumerate(archivos, 1):
            nombre = archivo["name"]
            tamano = int(archivo.get("size", 0))
            tamano_mb = tamano / (1024 * 1024)
            fecha = archivo.get("createdTime", "N/A")
            print(f"  {i}. {nombre}  ({tamano_mb:.1f} MB, {fecha})")

        # 3. Seleccionar archivo
        print()
        nombre_input = input("Ingrese el nombre del archivo: ").strip()
        if not nombre_input:
            print("No se ingresó ningún nombre. Abortando.")
            return

        archivo_seleccionado = next((a for a in archivos if a["name"] == nombre_input), None)
        if archivo_seleccionado is None:
            print(f"Archivo '{nombre_input}' no encontrado en la lista. Abortando.")
            return

        # 4. Confirmar
        print(f"\nArchivo seleccionado: {archivo_seleccionado['name']}")
        confirmacion = input("¿Está seguro? Esto REEMPLAZARÁ toda la base de datos actual. (s/n): ").strip().lower()
        if confirmacion != "s":
            print("Operación cancelada.")
            return

        # 5. Descargar
        print("\nDescargando respaldo...")
        sql_bytes = await _descargar_archivo(service, archivo_seleccionado["id"])
        sql_content = sql_bytes.decode("utf-8")
        tamano_mb = len(sql_bytes) / (1024 * 1024)
        print(f"  Respaldo descargado ({tamano_mb:.1f} MB)")

        # 6. Restaurar
        print("\nRestaurando...")
        await _restaurar(sql_content, conn)

        print("\n¡Respaldo restaurado exitosamente!\n")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
