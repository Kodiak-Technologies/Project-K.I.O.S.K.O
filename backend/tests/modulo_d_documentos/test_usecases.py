import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.modulo_d_documentos.application.generar_boleta_usecase import GenerarBoletaUseCase
from app.modules.modulo_d_documentos.application.subir_boleta_drive_usecase import SubirBoletaDriveUseCase
from app.modules.modulo_d_documentos.application.generar_reporte_ventas_usecase import GenerarReporteVentasUseCase
from app.modules.modulo_d_documentos.application.generar_reporte_mas_vendidos_usecase import GenerarReporteMasVendidosUseCase
from app.modules.modulo_d_documentos.application.enviar_notificacion_usecase import EnviarNotificacionUseCase
from app.modules.modulo_d_documentos.domain.entities import Boleta, ConfigNotificaciones, Notificacion
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class MockVentaDataProvider:
    async def obtener_venta(self, venta_id: int) -> dict | None:
        if venta_id == 1:
            return {"id": 1, "total": 50.0, "metodo_pago": "EFECTIVO"}
        return None

    async def listar_ventas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        return [
            {"id": 1, "total": 50.0},
            {"id": 2, "total": 30.0},
        ]

    async def obtener_detalle_venta(self, venta_id: int) -> list[dict]:
        return [
            {"nombre": "Arroz", "cantidad": 2, "precio_unitario": 10.0, "subtotal": 20.0},
            {"nombre": "Azúcar", "cantidad": 1, "precio_unitario": 5.0, "subtotal": 5.0},
        ]


class MockConfiguracionProvider:
    async def obtener(self) -> dict:
        return {"nombre_negocio": "Mi Tienda", "logo_url": ""}


class MockBoletaRepository:
    def __init__(self):
        self.boletas = []
        self._contador = 0

    async def buscar_por_id(self, boleta_id: int) -> Boleta | None:
        for b in self.boletas:
            if b.id == boleta_id:
                return b
        return None

    async def buscar_por_venta_id(self, venta_id: int) -> Boleta | None:
        for b in self.boletas:
            if b.venta_id == venta_id:
                return b
        return None

    async def listar(self, desde=None, hasta=None, q=None) -> list[Boleta]:
        return self.boletas

    async def crear(self, boleta: Boleta) -> Boleta:
        self._contador += 1
        boleta.id = self._contador
        self.boletas.append(boleta)
        return boleta

    async def generar_siguiente_numero(self) -> str:
        return f"B001-{(self._contador + 1):06d}"


class MockArchivoDriveRepository:
    def __init__(self):
        self.archivos = []
        self._contador = 0

    async def crear(self, archivo):
        self._contador += 1
        archivo.id = self._contador
        self.archivos.append(archivo)
        return archivo

    async def actualizar_estado(self, archivo):
        return archivo


class MockDriveStorage:
    async def subir(self, archivo_bytes, nombre, carpeta) -> str:
        return "drive_file_id_123"

    async def obtener_url(self, file_id) -> str:
        return "https://drive.google.com/file/123"


class MockNotificacionRepository:
    def __init__(self):
        self.notificaciones = []
        self._contador = 0

    async def crear(self, notificacion):
        self._contador += 1
        notificacion.id = self._contador
        self.notificaciones.append(notificacion)
        return notificacion

    async def listar(self):
        return self.notificaciones

    async def marcar_leida(self, notificacion_id):
        for n in self.notificaciones:
            if n.id == notificacion_id:
                n.marcar_leida()
                return n
        return None


class MockConfigNotificacionesRepository:
    async def obtener(self) -> ConfigNotificaciones:
        return ConfigNotificaciones(id=1, canal_telegram_activo=False, canal_correo_activo=False)


class MockNotificacionSender:
    async def enviar(self, canal, titulo, mensaje) -> bool:
        return True


class MockReporteGenerator:
    async def generar_excel(self, datos, nombre) -> bytes:
        return b"excel data"


class TestGenerarBoletaUseCase:
    @pytest.mark.asyncio
    async def test_generar_boleta_exitoso(self):
        use_case = GenerarBoletaUseCase(
            MockBoletaRepository(),
            MockVentaDataProvider(),
            MockConfiguracionProvider(),
        )
        boleta = await use_case.ejecutar(venta_id=1)
        assert boleta.numero.startswith("B001-")
        assert boleta.total == 50.0
        assert boleta.venta_id == 1

    @pytest.mark.asyncio
    async def test_venta_no_existe(self):
        use_case = GenerarBoletaUseCase(
            MockBoletaRepository(),
            MockVentaDataProvider(),
            MockConfiguracionProvider(),
        )
        with pytest.raises(NoEncontradoError):
            await use_case.ejecutar(venta_id=999)

    @pytest.mark.asyncio
    async def test_venta_ya_tiene_boleta(self):
        repo = MockBoletaRepository()
        await repo.crear(Boleta(id=None, venta_id=1, numero="B001-000001", total=50.0))
        use_case = GenerarBoletaUseCase(repo, MockVentaDataProvider(), MockConfiguracionProvider())
        with pytest.raises(ValidacionError):
            await use_case.ejecutar(venta_id=1)


class TestSubirBoletaDriveUseCase:
    @pytest.mark.asyncio
    async def test_subir_boleta_exitoso(self):
        boleta_repo = MockBoletaRepository()
        await boleta_repo.crear(Boleta(id=None, venta_id=1, numero="B001-000001", total=50.0))
        use_case = SubirBoletaDriveUseCase(boleta_repo, MockDriveStorage(), MockArchivoDriveRepository())
        archivo = await use_case.ejecutar(boleta_id=1)
        assert archivo.estado == "SUBIDO"
        assert archivo.drive_file_id == "drive_file_id_123"


class TestGenerarReporteVentasUseCase:
    @pytest.mark.asyncio
    async def test_generar_resumen(self):
        use_case = GenerarReporteVentasUseCase(MockVentaDataProvider())
        resumen = await use_case.ejecutar(desde="2026-01-01", hasta="2026-12-31")
        assert resumen.total_vendido == 80.0
        assert resumen.numero_ventas == 2
        assert resumen.ticket_promedio == 40.0
        assert len(resumen.top_productos) > 0


class TestGenerarReporteMasVendidosUseCase:
    @pytest.mark.asyncio
    async def test_ranking_unidades(self):
        use_case = GenerarReporteMasVendidosUseCase(MockVentaDataProvider())
        ranking = await use_case.ejecutar(desde="2026-01-01", hasta="2026-12-31", criterio="unidades")
        assert len(ranking) > 0
        assert ranking[0].nombre == "Arroz"

    @pytest.mark.asyncio
    async def test_ranking_monto(self):
        use_case = GenerarReporteMasVendidosUseCase(MockVentaDataProvider())
        ranking = await use_case.ejecutar(desde="2026-01-01", hasta="2026-12-31", criterio="monto")
        assert len(ranking) > 0


class TestEnviarNotificacionUseCase:
    @pytest.mark.asyncio
    async def test_enviar_y_registrar(self):
        use_case = EnviarNotificacionUseCase(
            MockNotificacionSender(),
            MockNotificacionRepository(),
            MockConfigNotificacionesRepository(),
        )
        noti = await use_case.ejecutar(tipo="SISTEMA", titulo="Test", mensaje="Mensaje de prueba")
        assert noti.id is not None
        assert noti.tipo == "SISTEMA"
        assert noti.titulo == "Test"
