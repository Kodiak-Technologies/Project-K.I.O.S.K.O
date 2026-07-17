import pytest

from app.modules.modulo_d_documentos.domain.value_objects import (
    CanalNotificacion,
    EstadoArchivoDrive,
    EstadoRespaldo,
    NivelDetalle,
    NumeroBoleta,
    RutaArchivo,
    TipoNotificacion,
)
from app.modules.modulo_d_documentos.domain.entities import (
    ArchivoDrive,
    Boleta,
    ConfigNotificaciones,
    Notificacion,
    Respaldo,
    ResumenReporte,
    TopProducto,
)
from app.shared.kernel.exceptions import ValidacionError
from datetime import datetime, timezone


class TestNumeroBoleta:
    def test_formato_valido(self):
        numero = NumeroBoleta("B001-000001")
        assert numero.valor == "B001-000001"
        assert str(numero) == "B001-000001"

    def test_formato_invalido(self):
        with pytest.raises(ValidacionError):
            NumeroBoleta("MALO")

    def test_formato_sin_guion(self):
        with pytest.raises(ValidacionError):
            NumeroBoleta("B001000001")

    def test_formato_muy_corto(self):
        with pytest.raises(ValidacionError):
            NumeroBoleta("B01-001")

    def test_igualdad(self):
        a = NumeroBoleta("B001-000001")
        b = NumeroBoleta("B001-000001")
        assert a == b

    def test_hash(self):
        a = NumeroBoleta("B001-000001")
        b = NumeroBoleta("B001-000001")
        assert hash(a) == hash(b)


class TestRutaArchivo:
    def test_ruta_valida(self):
        ruta = RutaArchivo("boletas/2026/07/file.png")
        assert ruta.valor == "boletas/2026/07/file.png"

    def test_ruta_vacia(self):
        with pytest.raises(ValidacionError):
            RutaArchivo("")

    def test_ruta_solo_espacios(self):
        with pytest.raises(ValidacionError):
            RutaArchivo("   ")

    def test_igualdad(self):
        a = RutaArchivo("file.png")
        b = RutaArchivo("file.png")
        assert a == b


class TestEnums:
    def test_canal_notificacion(self):
        assert CanalNotificacion.CORREO == "CORREO"
        assert CanalNotificacion.TELEGRAM == "TELEGRAM"
        assert CanalNotificacion.AMBOS == "AMBOS"

    def test_tipo_notificacion(self):
        assert TipoNotificacion.STOCK_BAJO == "STOCK_BAJO"
        assert TipoNotificacion.CIERRE_CAJA == "CIERRE_CAJA"

    def test_estado_archivo_drive(self):
        assert EstadoArchivoDrive.PENDIENTE == "PENDIENTE"
        assert EstadoArchivoDrive.SUBIDO == "SUBIDO"
        assert EstadoArchivoDrive.FALLIDO == "FALLIDO"

    def test_estado_respaldo(self):
        assert EstadoRespaldo.PENDIENTE == "PENDIENTE"
        assert EstadoRespaldo.COMPLETADO == "COMPLETADO"

    def test_nivel_detalle(self):
        assert NivelDetalle.BAJO == "BAJO"
        assert NivelDetalle.MEDIO == "MEDIO"
        assert NivelDetalle.ALTO == "ALTO"


class TestBoleta:
    def test_created_at_automatico(self):
        boleta = Boleta(id=None, venta_id=1, numero="B001-000001", total=10.0)
        assert boleta.emitida_en is not None

    def test_url_pdf_nullable(self):
        boleta = Boleta(id=None, venta_id=1, numero="B001-000001", total=10.0)
        assert boleta.url_pdf is None


class TestArchivoDrive:
    def test_estado_default_pendiente(self):
        archivo = ArchivoDrive(id=None, boleta_id=1, archivo_nombre="test.png", carpeta="boletas/")
        assert archivo.estado == EstadoArchivoDrive.PENDIENTE.value
        assert archivo.intentos == 0

    def test_esta_subido(self):
        archivo = ArchivoDrive(id=None, boleta_id=1, archivo_nombre="test.png", carpeta="boletas/", estado="SUBIDO")
        assert archivo.esta_subido is True

    def test_esta_pendiente(self):
        archivo = ArchivoDrive(id=None, boleta_id=1, archivo_nombre="test.png", carpeta="boletas/")
        assert archivo.esta_pendiente is True


class TestNotificacion:
    def test_marcar_leida(self):
        noti = Notificacion(id=1, tipo="SISTEMA", titulo="Test", mensaje="Test")
        assert noti.leida is False
        noti.marcar_leida()
        assert noti.leida is True

    def test_created_at_automatico(self):
        noti = Notificacion(id=1, tipo="SISTEMA", titulo="Test", mensaje="Test")
        assert noti.created_at is not None


class TestConfigNotificaciones:
    def test_defaults(self):
        config = ConfigNotificaciones()
        assert config.canal_telegram_activo is True
        assert config.canal_correo_activo is False
        assert config.nivel_detalle == "MEDIO"


class TestRespaldo:
    def test_estado_default_pendiente(self):
        respaldo = Respaldo(id=None, archivo_nombre="backup.dump")
        assert respaldo.estado == EstadoRespaldo.PENDIENTE.value

    def test_expira_en_30_dias(self):
        respaldo = Respaldo(id=None, archivo_nombre="backup.dump")
        assert respaldo.expira_en is not None

    def test_esta_completado(self):
        respaldo = Respaldo(id=None, archivo_nombre="backup.dump", estado="COMPLETADO")
        assert respaldo.esta_completado is True

    def test_no_esta_completado(self):
        respaldo = Respaldo(id=None, archivo_nombre="backup.dump")
        assert respaldo.esta_completado is False

    def test_expirado(self):
        from datetime import timedelta
        respaldo = Respaldo(id=None, archivo_nombre="backup.dump")
        respaldo.expira_en = datetime.now(timezone.utc) - timedelta(days=1)
        assert respaldo.expirado is True

    def test_no_expirado(self):
        from datetime import timedelta
        respaldo = Respaldo(id=None, archivo_nombre="backup.dump")
        respaldo.expira_en = datetime.now(timezone.utc) + timedelta(days=1)
        assert respaldo.expirado is False


class TestResumenReporte:
    def test_calcular_ticket_promedio(self):
        resumen = ResumenReporte(desde="2026-01-01", hasta="2026-12-31", total_vendido=100.0, numero_ventas=10)
        resumen.calcular_ticket_promedio()
        assert resumen.ticket_promedio == 10.0

    def test_calcular_ticket_cero_ventas(self):
        resumen = ResumenReporte(desde="2026-01-01", hasta="2026-12-31", total_vendido=0.0, numero_ventas=0)
        resumen.calcular_ticket_promedio()
        assert resumen.ticket_promedio == 0.0


class TestBoletaPngGenerator:
    @pytest.mark.asyncio
    async def test_genera_bytes_validos(self):
        from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.boleta_png_generator import BoletaPngGenerator
        gen = BoletaPngGenerator()
        resultado = await gen.generar(
            numero="B001-000001", total=150.0, fecha="2026-07-15",
            productos=[{"nombre": "Arroz", "cantidad": 2, "precio_unitario": 25.0, "subtotal": 50.0}],
            nombre_negocio="Mi Tienda",
        )
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    @pytest.mark.asyncio
    async def test_genera_png_con_productos(self):
        from app.modules.modulo_d_documentos.infrastructure.adapters.document_generators.boleta_png_generator import BoletaPngGenerator
        gen = BoletaPngGenerator()
        productos = [
            {"nombre": "Arroz", "cantidad": 2, "precio_unitario": 25.0, "subtotal": 50.0},
            {"nombre": "Aceite", "cantidad": 1, "precio_unitario": 100.0, "subtotal": 100.0},
            {"nombre": "Leche", "cantidad": 3, "precio_unitario": 5.0, "subtotal": 15.0},
        ]
        resultado = await gen.generar(
            numero="B001-000002", total=165.0, fecha="2026-07-15",
            productos=productos, nombre_negocio="Mi Tienda",
        )
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0
