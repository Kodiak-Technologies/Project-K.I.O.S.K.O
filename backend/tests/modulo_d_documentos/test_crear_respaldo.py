"""Respaldo manual bajo demanda.

Mismo flujo que la tarea automática diaria (registro, volcado SQL y subida a
Drive) pero sin el chequeo de hora: se ejecuta cuando un ADMIN lo pide. Los
tests no tocan la BD ni Drive: el volcado y el Drive vienen como dobles.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.modulo_d_documentos.application.crear_respaldo_usecase import (
    CrearRespaldoUseCase,
)
from app.shared.kernel.exceptions import ValidacionError

DATABASE_URL = "postgresql+asyncpg://tienda:tienda@localhost:5432/tienda_sistema"


class RespaldoRepoFake:
    """Registra cada escritura con el estado que quedó al hacerla."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[str, str]] = []
        self._ultimo_id = 0

    async def crear(self, respaldo):
        self._ultimo_id += 1
        respaldo.id = self._ultimo_id
        self.llamadas.append(("crear", respaldo.estado))
        return respaldo

    async def actualizar(self, respaldo):
        self.llamadas.append(("actualizar", respaldo.estado))
        return respaldo


class DriveFake:
    def __init__(self, falla: bool = False) -> None:
        self.subidas: list[dict] = []
        self._falla = falla

    async def subir(self, archivo_bytes: bytes, nombre: str, carpeta: str) -> str:
        if self._falla:
            raise RuntimeError("Drive no disponible")
        self.subidas.append({"bytes": archivo_bytes, "nombre": nombre, "carpeta": carpeta})
        return "file-id-123"


DUMP = b"-- volcado de la base\nCREATE TABLE productos (id int);\n"


async def _dump_falso(db_params: dict) -> bytes:
    assert db_params["dbname"] == "tienda_sistema"
    return DUMP


def _carpeta_esperada() -> str:
    ahora = datetime.now(timezone.utc)
    return f"respaldos/{ahora.strftime('%Y')}/{ahora.strftime('%m')}"


class TestRespaldoManual:
    async def test_completa_el_respaldo_y_lo_sube_a_drive(self):
        repo, drive = RespaldoRepoFake(), DriveFake()
        caso = CrearRespaldoUseCase(
            repo, drive, database_url=DATABASE_URL, generar_dump=_dump_falso
        )

        respaldo = await caso.ejecutar()

        assert respaldo.estado == "COMPLETADO"
        assert respaldo.drive_file_id == "file-id-123"
        assert respaldo.tamano_bytes == len(DUMP)
        assert respaldo.id is not None

    async def test_pasa_de_pendiente_a_completado(self):
        repo, drive = RespaldoRepoFake(), DriveFake()
        caso = CrearRespaldoUseCase(
            repo, drive, database_url=DATABASE_URL, generar_dump=_dump_falso
        )

        await caso.ejecutar()

        assert repo.llamadas == [("crear", "PENDIENTE"), ("actualizar", "COMPLETADO")]

    async def test_sube_a_la_carpeta_del_anio_y_mes_actual(self):
        repo, drive = RespaldoRepoFake(), DriveFake()
        caso = CrearRespaldoUseCase(
            repo, drive, database_url=DATABASE_URL, generar_dump=_dump_falso
        )

        respaldo = await caso.ejecutar()

        subida = drive.subidas[0]
        assert subida["carpeta"] == _carpeta_esperada()
        assert subida["nombre"] == respaldo.archivo_nombre
        assert respaldo.archivo_nombre.startswith("tienda_sistema_")
        assert respaldo.archivo_nombre.endswith(".sql")

    async def test_el_respaldo_expira_en_cuatro_dias(self):
        repo, drive = RespaldoRepoFake(), DriveFake()
        caso = CrearRespaldoUseCase(
            repo, drive, database_url=DATABASE_URL, generar_dump=_dump_falso
        )

        respaldo = await caso.ejecutar()

        esperado = datetime.now(timezone.utc) + timedelta(days=4)
        diferencia = abs((respaldo.expira_en - esperado).total_seconds())
        assert diferencia < 60

    async def test_falla_de_drive_marca_el_respaldo_como_fallido(self):
        repo, drive = RespaldoRepoFake(), DriveFake(falla=True)
        caso = CrearRespaldoUseCase(
            repo, drive, database_url=DATABASE_URL, generar_dump=_dump_falso
        )

        with pytest.raises(RuntimeError):
            await caso.ejecutar()

        assert repo.llamadas == [("crear", "PENDIENTE"), ("actualizar", "FALLIDO")]

    async def test_falla_del_volumen_tambien_marca_fallido(self):
        async def _dump_roto(db_params):
            raise OSError("no hay conexión con la base")

        repo, drive = RespaldoRepoFake(), DriveFake()
        caso = CrearRespaldoUseCase(
            repo, drive, database_url=DATABASE_URL, generar_dump=_dump_roto
        )

        with pytest.raises(OSError):
            await caso.ejecutar()

        assert repo.llamadas == [("crear", "PENDIENTE"), ("actualizar", "FALLIDO")]
        assert drive.subidas == []

    async def test_sin_database_url_no_crea_el_registro(self):
        repo, drive = RespaldoRepoFake(), DriveFake()
        caso = CrearRespaldoUseCase(repo, drive, database_url="", generar_dump=_dump_falso)

        with pytest.raises(ValidacionError):
            await caso.ejecutar()

        assert repo.llamadas == []
        assert drive.subidas == []

    async def test_recibe_por_parametro_el_url_de_la_base(self):
        """El volcado usa la URL que le pasaron, no una global escondida."""
        params_vistos = {}

        async def _dump(db_params):
            params_vistos.update(db_params)
            return DUMP

        repo, drive = RespaldoRepoFake(), DriveFake()
        caso = CrearRespaldoUseCase(
            repo,
            drive,
            database_url="postgresql+asyncpg://otra:clave@dbhost:5433/otra_bd",
            generar_dump=_dump,
        )

        await caso.ejecutar()

        assert params_vistos["host"] == "dbhost"
        assert params_vistos["port"] == 5433
        assert params_vistos["dbname"] == "otra_bd"
