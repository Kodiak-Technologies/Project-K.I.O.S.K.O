import io
import logging
from datetime import datetime, timedelta, timezone


from app.modules.modulo_d_documentos.domain.entities import Respaldo
from app.modules.modulo_d_documentos.domain.ports.respaldo_repository_port import RespaldoRepositoryPort
from app.modules.modulo_d_documentos.domain.ports.drive_storage_port import DriveStoragePort
from app.shared.config.settings import settings
from app.shared.database.asyncpg_directo import conectar as conectar_directo

logger = logging.getLogger(__name__)

# Orden de tablas respetando foreign keys.
#
# OJO al tocar esta lista: `tablas_a_volcar` filtra por las que existen en la
# BD, así que una tabla que falte acá NO se respalda y NO avisa. Se había
# quedado vieja y dejaba afuera todo el lado de proveedores/ingresos del
# Módulo B (7 tablas), además de listar 3 tablas del fiado ya eliminadas.
# Debe coincidir con `db/schema.sql`.
TABLAS_ORDEN = [
    # Módulo A — seguridad
    "roles",
    "permisos",
    "rol_permisos",
    "usuarios",
    "sesiones",
    "bitacora_auditoria",
    "configuracion_negocio",
    # Módulo B — inventario
    "categorias",
    "proveedores",
    "productos",
    "solicitudes_ingreso",
    "detalle_solicitud",
    "pagos_proveedor",
    "movimientos_inventario",
    "historial_precios",
    # Módulo C — ventas y caja
    "metodos_pago",
    "turnos_caja",
    "arqueos",
    "ventas",
    "detalles_venta",
    "pagos_venta",
    "anulaciones",
    # Módulo D — documentos
    "notificaciones",
    "config_notificaciones",
    "respaldos",
    "oauth_tokens",
]


def _parsear_database_url(url: str) -> dict:
    """Extrae host, port, user, password, dbname de DATABASE_URL."""
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


def _escapar_valor(valor) -> str:
    """Convierte un valor Python a representación SQL literal."""
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, datetime):
        return f"'{valor.isoformat()}'"
    s = str(valor)
    s = s.replace("'", "''")
    return f"'{s}'"


async def _generar_dump_sql(db_params: dict) -> bytes:
    """Genera un archivo .sql con la estructura y datos de todas las tablas."""
    conn = await conectar_directo(
        host=db_params["host"],
        port=db_params["port"],
        user=db_params["user"],
        password=db_params["password"],
        database=db_params["dbname"],
    )

    buffer = io.StringIO()
    buffer.write("-- Respaldo generado automáticamente\n")
    buffer.write(f"-- Fecha: {datetime.now(timezone.utc).isoformat()}\n\n")

    try:
        # Obtener tablas del schema public
        tablas_bd = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        nombres_bd = {t["tablename"] for t in tablas_bd}

        # Usar orden predefinido para las que existen, agregar las demás al final
        tablas_a_volcar = [t for t in TABLAS_ORDEN if t in nombres_bd]
        tablas_a_volcar.extend(sorted(nombres_bd - set(tablas_a_volcar)))

        for tabla in tablas_a_volcar:
            # Obtener columnas
            columnas = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position
                """,
                tabla,
            )

            if not columnas:
                continue

            nombres_col = [c["column_name"] for c in columnas]

            # Obtener datos
            filas = await conn.fetch(f'SELECT * FROM "{tabla}"')

            buffer.write(f"-- Tabla: {tabla} ({len(filas)} registros)\n")
            buffer.write(f'DELETE FROM "{tabla}";\n')

            if filas:
                for fila in filas:
                    valores = [_escapar_valor(fila[n]) for n in nombres_col]
                    cols = ", ".join(f'"{n}"' for n in nombres_col)
                    vals = ", ".join(valores)
                    buffer.write(f'INSERT INTO "{tabla}" ({cols}) VALUES ({vals});\n')

            buffer.write("\n")

        # Resetear secuencias
        buffer.write("-- Resetear secuencias\n")
        for tabla in tablas_a_volcar:
            tiene_id = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=$1 AND column_name='id')",
                tabla,
            )
            if not tiene_id:
                continue
            seq = await conn.fetchval(
                "SELECT pg_get_serial_sequence($1, 'id')", tabla
            )
            if seq:
                max_id = await conn.fetchval(f'SELECT COALESCE(MAX(id), 0) FROM "{tabla}"')
                if max_id is not None:
                    buffer.write(f"SELECT setval('{seq}', {max_id});\n")

    finally:
        await conn.close()

    return buffer.getvalue().encode("utf-8")


class CrearRespaldoUseCase:
    def __init__(
        self,
        respaldo_repository: RespaldoRepositoryPort,
        drive_storage: DriveStoragePort,
    ) -> None:
        self._repo = respaldo_repository
        self._drive = drive_storage

    async def ejecutar(self, usuario_id: int | None = None) -> Respaldo:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        nombre = f"tienda_sistema_{timestamp}.sql"

        ahora = datetime.now(timezone.utc)
        respaldo = Respaldo(
            id=None,
            archivo_nombre=nombre,
            estado="PENDIENTE",
            expira_en=ahora + timedelta(days=21),
            usuario_id=usuario_id,
        )
        respaldo = await self._repo.crear(respaldo)

        database_url = settings.database_url
        if not database_url:
            respaldo.estado = "FALLIDO"
            return await self._repo.actualizar(respaldo)

        try:
            db_params = _parsear_database_url(database_url)
            sql_bytes = await _generar_dump_sql(db_params)

            anio = ahora.strftime("%Y")
            mes = ahora.strftime("%m")
            carpeta_drive = f"respaldos/{anio}/{mes}"
            drive_file_id = await self._drive.subir(
                archivo_bytes=sql_bytes,
                nombre=nombre,
                carpeta=carpeta_drive,
            )

            respaldo.estado = "COMPLETADO"
            respaldo.tamano_bytes = len(sql_bytes)
            respaldo.drive_file_id = drive_file_id
            return await self._repo.actualizar(respaldo)

        except Exception as e:
            logger.error("Error creando respaldo: %s", str(e))
            respaldo.estado = "FALLIDO"
            return await self._repo.actualizar(respaldo)


class ObtenerRutaRespaldoUseCase:
    """Descarga un respaldo desde Drive y retorna los bytes."""

    def __init__(
        self,
        respaldo_repository: RespaldoRepositoryPort,
        drive_storage: DriveStoragePort,
    ) -> None:
        self._repo = respaldo_repository
        self._drive = drive_storage

    async def ejecutar(self, respaldo_id: int) -> tuple[bytes, str]:
        respaldo = await self._repo.buscar_por_id(respaldo_id)
        if respaldo is None:
            raise ValueError("Respaldo no encontrado")
        if not respaldo.drive_file_id:
            raise FileNotFoundError("El respaldo no tiene archivo asociado en Drive")

        contenido = await self._drive.descargar(respaldo.drive_file_id)
        return contenido, respaldo.archivo_nombre


class RestaurarRespaldoUseCase:
    def __init__(
        self,
        respaldo_repository: RespaldoRepositoryPort,
        drive_storage: DriveStoragePort,
    ) -> None:
        self._repo = respaldo_repository
        self._drive = drive_storage

    async def ejecutar(self, respaldo_id: int) -> bool:
        respaldo = await self._repo.buscar_por_id(respaldo_id)
        if respaldo is None:
            raise ValueError("Respaldo no encontrado")
        if not respaldo.drive_file_id:
            raise FileNotFoundError("El respaldo no tiene archivo asociado en Drive")

        database_url = settings.database_url
        if not database_url:
            raise ValueError("DATABASE_URL no configurada")

        sql_bytes = await self._drive.descargar(respaldo.drive_file_id)
        sql_content = sql_bytes.decode("utf-8")

        db_params = _parsear_database_url(database_url)
        conn = await conectar_directo(
            host=db_params["host"],
            port=db_params["port"],
            user=db_params["user"],
            password=db_params["password"],
            database=db_params["dbname"],
        )

        try:
            await conn.execute("SET session_replication_role = 'replica'")

            for linea in sql_content.split("\n"):
                linea = linea.strip()
                if not linea or linea.startswith("--"):
                    continue
                if linea.upper().startswith("SELECT SETVAL"):
                    await conn.execute(linea)
                else:
                    await conn.execute(linea)

            await conn.execute("SET session_replication_role = 'origin'")
            return True

        except Exception as e:
            logger.error("Error restaurando respaldo: %s", str(e))
            return False

        finally:
            await conn.close()
