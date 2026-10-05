"""Contrato HTTP de `POST /respaldos` (respaldo manual).

Se levanta una mini-app con solo el router de respaldos: la autenticación, el
repositorio y Drive se reemplazan por dobles. Así se comprueba el código de
estado y el rol exigido sin tocar la base real.
"""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure import dependencies as seguridad
from app.modules.modulo_d_documentos.infrastructure import dependencies as dependencias
from app.modules.modulo_d_documentos.infrastructure.http import respaldos_router as modulo
from app.shared.http.error_handlers import registrar_error_handlers
from app.shared.kernel.exceptions import NoAutorizadoError

DATABASE_URL = "postgresql+asyncpg://tienda:tienda@localhost:5432/tienda_sistema"
DUMP = b"CREATE TABLE productos (id int);\n"


class RespaldoRepoFake:
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
        self.subidas: list[str] = []
        self._falla = falla

    async def subir(self, archivo_bytes: bytes, nombre: str, carpeta: str) -> str:
        if self._falla:
            raise RuntimeError("Drive no disponible")
        self.subidas.append(carpeta)
        return "file-id-123"


class SesionFake:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


async def _dump(db_params: dict) -> bytes:
    return DUMP


async def _usuario_actual(request: Request) -> Usuario:
    """Doble de `get_current_user`: el rol llega por header para poder
    simular a un ADMIN, a un rol menor y a un request sin token."""
    rol = request.headers.get("X-Rol", "ADMIN")
    if rol == "SIN_TOKEN":
        raise NoAutorizadoError("Falta el token de autenticación.")
    return Usuario(
        id=1,
        username="admin",
        nombre="Admin",
        password_hash="x",
        rol_id=1,
        rol_nombre=rol,
    )


class Escenario:
    def __init__(self, falla_drive: bool = False) -> None:
        self.repo = RespaldoRepoFake()
        self.drive = DriveFake(falla=falla_drive)
        self.sesion = SesionFake()

        async def _db():
            yield self.sesion

        self.app = FastAPI()
        registrar_error_handlers(self.app)
        self.app.include_router(modulo.router)
        self.app.dependency_overrides[seguridad.get_current_user] = _usuario_actual
        self.app.dependency_overrides[dependencias.get_respaldo_repository] = lambda: self.repo
        self.app.dependency_overrides[dependencias.get_drive_storage] = lambda: self.drive
        self.app.dependency_overrides[dependencias.get_db] = _db

        # El volcado real necesita la base: lo cambiamos por el doble.
        _crear = modulo.CrearRespaldoUseCase

        def _caso_de_prueba(respaldo_repo, drive_storage):
            return _crear(respaldo_repo, drive_storage, database_url=DATABASE_URL, generar_dump=_dump)

        self._caso_original = modulo.CrearRespaldoUseCase
        modulo.CrearRespaldoUseCase = _caso_de_prueba

        self.client = TestClient(self.app, raise_server_exceptions=False)

    def cerrar(self) -> None:
        modulo.CrearRespaldoUseCase = self._caso_original

    def post(self, rol: str = "ADMIN"):
        return self.client.post("/respaldos", headers={"X-Rol": rol})


class TestRespaldoManualApi:
    def test_admin_recibe_201_con_el_respaldo_completado(self):
        esc = Escenario()
        try:
            r = esc.post()
        finally:
            esc.cerrar()

        assert r.status_code == 201
        body = r.json()
        assert body["estado"] == "COMPLETADO"
        assert body["drive_file_id"] == "file-id-123"
        assert body["tamano_bytes"] == len(DUMP)
        assert body["archivo_nombre"].endswith(".sql")
        assert esc.repo.llamadas == [("crear", "PENDIENTE"), ("actualizar", "COMPLETADO")]

    def test_sin_token_responde_401(self):
        esc = Escenario()
        try:
            r = esc.post(rol="SIN_TOKEN")
        finally:
            esc.cerrar()

        assert r.status_code == 401
        assert esc.repo.llamadas == []

    def test_rol_no_admin_responde_403(self):
        esc = Escenario()
        try:
            r = esc.post(rol="CAJERO")
        finally:
            esc.cerrar()

        assert r.status_code == 403
        assert esc.repo.llamadas == []

    def test_falla_de_drive_devuelve_500_y_marca_fallido(self):
        esc = Escenario(falla_drive=True)
        try:
            r = esc.post()
        finally:
            esc.cerrar()

        assert r.status_code == 500
        assert "Error al generar el respaldo" in r.json()["detail"]
        # El FALLIDO se confirma explícitamente: `get_db` haría rollback si no.
        assert esc.sesion.commits >= 1
        assert esc.repo.llamadas == [("crear", "PENDIENTE"), ("actualizar", "FALLIDO")]
