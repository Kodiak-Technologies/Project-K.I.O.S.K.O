"""Dominio del Módulo A: entidades y value objects.

Python puro, sin BD ni HTTP. Se prueba la REGLA que expresa cada método, no su
implementación: qué significa estar bloqueado, cuándo una sesión sigue siendo
válida, qué TTL le toca a cada rol.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.modulo_a_seguridad.domain.entities import (
    ConfiguracionNegocio,
    Permiso,
    RegistroAuditoria,
    Rol,
    SesionToken,
    Usuario,
)
from app.modules.modulo_a_seguridad.domain.value_objects import (
    PasswordPlano,
    Username,
)
from app.shared.kernel.exceptions import ValidacionError

AHORA = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _usuario(**kwargs) -> Usuario:
    base = dict(
        id=1,
        username="cajero1",
        nombre="Ana Torres",
        password_hash="hash",
        rol_id=2,
        rol_nombre="CAJERO",
    )
    base.update(kwargs)
    return Usuario(**base)  # type: ignore[arg-type]


class TestUsuarioBloqueo:
    def test_sin_fecha_de_bloqueo_no_esta_bloqueado(self):
        assert _usuario(bloqueado_hasta=None).esta_bloqueado(AHORA) is False

    def test_bloqueo_futuro_lo_mantiene_bloqueado(self):
        u = _usuario(bloqueado_hasta=AHORA + timedelta(minutes=15))
        assert u.esta_bloqueado(AHORA) is True

    def test_bloqueo_vencido_lo_libera(self):
        u = _usuario(bloqueado_hasta=AHORA - timedelta(seconds=1))
        assert u.esta_bloqueado(AHORA) is False

    def test_el_instante_exacto_del_vencimiento_ya_no_bloquea(self):
        """En el borde el usuario entra: el bloqueo es 'hasta', no 'hasta inclusive'."""
        u = _usuario(bloqueado_hasta=AHORA)
        assert u.esta_bloqueado(AHORA) is False

    def test_sin_argumento_usa_el_reloj(self):
        u = _usuario(bloqueado_hasta=datetime.now(timezone.utc) + timedelta(hours=1))
        assert u.esta_bloqueado() is True


class TestUsuarioPuedeIniciarSesion:
    def test_activo_y_no_eliminado_puede(self):
        assert _usuario().puede_iniciar_sesion() is True

    def test_inactivo_no_puede(self):
        assert _usuario(activo=False).puede_iniciar_sesion() is False

    def test_eliminado_no_puede_aunque_este_activo(self):
        u = _usuario(activo=True, deleted_at=AHORA)
        assert u.eliminado is True
        assert u.puede_iniciar_sesion() is False

    def test_bloqueado_temporalmente_SI_puede(self):
        """`puede_iniciar_sesion` mira baja/inactividad, no el bloqueo por
        intentos fallidos: ese es temporal y lo evalúa el caso de uso aparte."""
        u = _usuario(bloqueado_hasta=AHORA + timedelta(minutes=15))
        assert u.puede_iniciar_sesion() is True


class TestSesionToken:
    def _sesion(self, **kwargs) -> SesionToken:
        base = dict(
            id=1,
            usuario_id=1,
            refresh_token_hash="h",
            ip="",
            user_agent="",
            expira_en=AHORA + timedelta(days=1),
        )
        base.update(kwargs)
        return SesionToken(**base)  # type: ignore[arg-type]

    def test_vigente_y_no_revocada_es_valida(self):
        assert self._sesion().es_valida(AHORA) is True

    def test_revocada_no_es_valida_aunque_no_haya_vencido(self):
        assert self._sesion(revocada=True).es_valida(AHORA) is False

    def test_vencida_no_es_valida(self):
        s = self._sesion(expira_en=AHORA - timedelta(seconds=1))
        assert s.es_valida(AHORA) is False

    def test_el_instante_exacto_de_expiracion_ya_no_vale(self):
        assert self._sesion(expira_en=AHORA).es_valida(AHORA) is False


class TestConfiguracionNegocio:
    def test_admin_recibe_su_propio_ttl(self):
        c = ConfiguracionNegocio(id=1, nombre_negocio="Kiosco")
        assert c.ttl_para_rol("ADMIN") == c.session_ttl_admin_minutos

    def test_cualquier_rol_que_no_sea_admin_recibe_el_de_cajero(self):
        c = ConfiguracionNegocio(id=1, nombre_negocio="Kiosco")
        assert c.ttl_para_rol("CAJERO") == c.session_ttl_cajero_minutos
        # Un rol desconocido cae del lado restrictivo, no del permisivo.
        assert c.ttl_para_rol("DESCONOCIDO") == c.session_ttl_cajero_minutos

    def test_el_ttl_de_admin_es_mas_largo_que_el_de_cajero(self):
        c = ConfiguracionNegocio(id=1, nombre_negocio="Kiosco")
        assert c.session_ttl_admin_minutos > c.session_ttl_cajero_minutos


class TestEntidadesSimples:
    def test_rol_y_permiso_tienen_descripcion_opcional(self):
        assert Rol(id=1, nombre="ADMIN").descripcion == ""
        assert Permiso(id=1, codigo="ventas.anular").descripcion == ""

    def test_registro_auditoria_admite_usuario_anonimo(self):
        """Un login fallido con un username inexistente no tiene usuario_id."""
        r = RegistroAuditoria(
            id=None, usuario_id=None, rol="", accion="login_fallido", entidad="usuarios"
        )
        assert r.usuario_id is None
        assert r.valor_anterior is None and r.valor_nuevo is None


class TestUsername:
    @pytest.mark.parametrize("valor", ["abc", "cajero1", "admin_2", "a" * 30, "u_1"])
    def test_acepta_formatos_validos(self, valor):
        assert Username(valor).valor == valor

    @pytest.mark.parametrize(
        "valor,motivo",
        [
            ("ab", "menos de 3 caracteres"),
            ("a" * 31, "más de 30 caracteres"),
            ("Cajero", "mayúsculas"),
            ("cajero 1", "espacios"),
            ("cajero-1", "guion medio"),
            ("cajero@casa", "arroba"),
            ("", "vacío"),
            ("ñoño1", "caracteres no ascii"),
        ],
    )
    def test_rechaza_formatos_invalidos(self, valor, motivo):
        with pytest.raises(ValidacionError):
            Username(valor)

    def test_es_inmutable(self):
        u = Username("cajero1")
        with pytest.raises(Exception):
            u.valor = "otro"  # type: ignore[misc]


class TestPasswordPlano:
    @pytest.mark.parametrize("valor", ["abcd1234", "Segura123", "a1" * 20])
    def test_acepta_las_que_cumplen_la_politica(self, valor):
        assert PasswordPlano(valor).valor == valor

    @pytest.mark.parametrize(
        "valor,motivo",
        [
            ("abc123", "menos de 8 caracteres"),
            ("abcdefgh", "sin números"),
            ("12345678", "sin letras"),
            ("", "vacía"),
        ],
    )
    def test_rechaza_las_que_no_cumplen(self, valor, motivo):
        with pytest.raises(ValidacionError):
            PasswordPlano(valor)

    def test_el_largo_minimo_es_8_exacto(self):
        PasswordPlano("abcd1234")  # 8: pasa
        with pytest.raises(ValidacionError):
            PasswordPlano("abc1234")  # 7: no
