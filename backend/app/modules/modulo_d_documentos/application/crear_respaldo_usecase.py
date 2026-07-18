import os
import subprocess
from datetime import datetime, timedelta, timezone

from app.modules.modulo_d_documentos.domain.entities import Respaldo
from app.modules.modulo_d_documentos.domain.ports.respaldo_repository_port import RespaldoRepositoryPort
from app.shared.config.settings import settings

BACKUPS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "scripts",
    "backups",
)


class CrearRespaldoUseCase:
    def __init__(self, respaldo_repository: RespaldoRepositoryPort):
        self._repo = respaldo_repository

    async def ejecutar(self) -> Respaldo:
        os.makedirs(BACKUPS_DIR, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        nombre = f"tienda_sistema_{timestamp}.dump"
        ruta = os.path.join(BACKUPS_DIR, nombre)

        respaldo = Respaldo(id=None, archivo_nombre=nombre, estado="PENDIENTE")
        respaldo = await self._repo.crear(respaldo)

        database_url = settings.database_url
        if not database_url:
            return respaldo

        try:
            partes = database_url.replace("postgresql+asyncpg://", "").split("@")
            auth = partes[0].split(":")
            host_db = partes[1].split("/")
            user, password = auth[0], auth[1]
            host_port = host_db[0].split(":")
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else "5432"
            dbname = host_db[1]

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            proc = subprocess.run(
                ["pg_dump", "-h", host, "-p", port, "-U", user, "-d", dbname, "-f", ruta, "--no-owner", "--no-acl"],
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )

            if proc.returncode != 0 or not os.path.exists(ruta):
                respaldo.estado = "FALLIDO"
                return await self._repo.actualizar(respaldo)

            tamano = os.path.getsize(ruta)
            respaldo.estado = "COMPLETADO"
            respaldo.tamano_bytes = tamano
            respaldo.expira_en = datetime.now(timezone.utc) + timedelta(days=30)
            return await self._repo.actualizar(respaldo)

        except Exception:
            respaldo.estado = "FALLIDO"
            return await self._repo.actualizar(respaldo)


class ObtenerRutaRespaldoUseCase:
    def __init__(self, respaldo_repository: RespaldoRepositoryPort):
        self._repo = respaldo_repository

    async def ejecutar(self, respaldo_id: int) -> tuple[str, str]:
        respaldo = await self._repo.buscar_por_id(respaldo_id)
        if respaldo is None:
            raise ValueError("Respaldo no encontrado")

        ruta = os.path.join(BACKUPS_DIR, respaldo.archivo_nombre)
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"Archivo {respaldo.archivo_nombre} no existe en disco")
        return ruta, respaldo.archivo_nombre
