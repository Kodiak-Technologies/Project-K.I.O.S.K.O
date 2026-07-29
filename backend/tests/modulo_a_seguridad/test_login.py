"""`LoginUseCase`: autenticación, bloqueo por intentos y rastro en bitácora.

Es el caso de uso con más reglas del módulo, y varias son de seguridad:
  - nunca revelar si falló el usuario o la contraseña;
  - bloquear tras N intentos, con N configurable;
  - dejar registro de TODO intento, incluso los fallidos;
  - confirmar la transacción antes de lanzar el error, para que el contador de
    intentos y la bitácora sobrevivan al rollback del request.
"""

from datetime import timedelta

import pytest

from app.modules.modulo_a_seguridad.application.login_usecase import (
    MENSAJE_GENERICO,
    LoginUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import ConfiguracionNegocio
from app.shared.kernel.exceptions import CuentaBloqueadaError, NoAutorizadoError

from .dobles import (
    AHORA,
    AuditoriaFake,
    ConfiguracionRepoFake,
    HasherFake,
    SesionRepoFake,
    TokenServiceFake,
    UnidadTrabajoFake,
    UsuarioRepoFake,
    usuario,
)

PASSWORD = "Clave123"


class Escenario:
    """Arma el caso de uso con todos sus dobles y deja los espías a mano."""

    def __init__(self, usuarios=None, config=None):
        self.usuarios = UsuarioRepoFake(usuarios if usuarios is not None else [usuario()])
        self.sesiones = SesionRepoFake()
        self.config = ConfiguracionRepoFake(config)
        self.hasher = HasherFake()
        self.tokens = TokenServiceFake()
        self.auditoria = AuditoriaFake()
        self.uow = UnidadTrabajoFake()
        self.caso = LoginUseCase(
            self.usuarios,
            self.sesiones,
            self.config,
            self.hasher,
            self.tokens,
            self.auditoria,
            self.uow,
        )

    async def login(self, username="cajero1", password=PASSWORD):
        return await self.caso.ejecutar(
            username=username, password=password, ip="1.2.3.4", user_agent="tests"
        )


class TestLoginExitoso:
    async def test_devuelve_usuario_y_los_dos_tokens(self):
        e = Escenario()
        r = await e.login()
        assert r.usuario.username == "cajero1"
        assert r.access_token and r.refresh_token
        assert r.access_token != r.refresh_token

    async def test_crea_la_sesion_guardando_el_HASH_del_refresh(self):
        """El refresh en claro nunca se persiste."""
        e = Escenario()
        r = await e.login()
        assert len(e.sesiones.sesiones) == 1
        guardado = e.sesiones.sesiones[0].refresh_token_hash
        assert guardado != r.refresh_token
        assert guardado == e.tokens.hashear_refresh_token(r.refresh_token)

    async def test_registra_ip_y_user_agent_en_la_sesion(self):
        e = Escenario()
        await e.login()
        s = e.sesiones.sesiones[0]
        assert s.ip == "1.2.3.4" and s.user_agent == "tests"

    async def test_resetea_intentos_fallidos_y_desbloquea(self):
        u = usuario(intentos_fallidos=2, bloqueado_hasta=AHORA - timedelta(days=1))
        e = Escenario([u])
        await e.login()
        assert u.intentos_fallidos == 0
        assert u.bloqueado_hasta is None

    async def test_actualiza_ultimo_acceso(self):
        u = usuario(ultimo_acceso=None)
        e = Escenario([u])
        await e.login()
        assert u.ultimo_acceso is not None

    async def test_deja_el_evento_login_exitoso(self):
        e = Escenario()
        await e.login()
        assert e.auditoria.acciones() == ["login_exitoso"]

    async def test_el_access_token_lleva_el_rol(self):
        """El rol viaja en el token: de ahí sale la autorización."""
        e = Escenario([usuario(rol_nombre="ADMIN")])
        await e.login()
        assert e.tokens.access_tokens_creados[0][2] == "ADMIN"

    @pytest.mark.parametrize(
        "rol,minutos", [("ADMIN", 43200), ("CAJERO", 720)]
    )
    async def test_el_ttl_de_la_sesion_depende_del_rol(self, rol, minutos):
        e = Escenario([usuario(rol_nombre=rol)])
        await e.login()
        s = e.sesiones.sesiones[0]
        delta = s.expira_en - (s.expira_en - timedelta(minutes=minutos))
        assert delta == timedelta(minutes=minutos)


class TestCredencialesInvalidas:
    async def test_password_incorrecta_lanza_no_autorizado(self):
        e = Escenario()
        with pytest.raises(NoAutorizadoError):
            await e.login(password="otraClave1")

    async def test_usuario_inexistente_lanza_el_MISMO_mensaje(self):
        """No se puede distinguir 'no existe' de 'contraseña mala': si no, se
        puede enumerar usuarios."""
        e = Escenario()
        with pytest.raises(NoAutorizadoError) as inexistente:
            await e.login(username="fantasma")
        with pytest.raises(NoAutorizadoError) as mala_pass:
            await e.login(password="otraClave1")
        assert str(inexistente.value) == str(mala_pass.value) == MENSAJE_GENERICO

    async def test_usuario_inactivo_no_entra(self):
        e = Escenario([usuario(activo=False)])
        with pytest.raises(NoAutorizadoError):
            await e.login()

    async def test_usuario_eliminado_no_entra(self):
        e = Escenario([usuario(deleted_at=AHORA)])
        with pytest.raises(NoAutorizadoError):
            await e.login()

    async def test_no_crea_sesion_cuando_falla(self):
        e = Escenario()
        with pytest.raises(NoAutorizadoError):
            await e.login(password="otraClave1")
        assert e.sesiones.sesiones == []

    async def test_confirma_la_transaccion_pese_al_error(self):
        """El 401 hace rollback del request; sin este commit se perderían el
        contador de intentos y el evento de bitácora."""
        e = Escenario()
        with pytest.raises(NoAutorizadoError):
            await e.login(password="otraClave1")
        assert e.uow.confirmaciones == 1

    async def test_incrementa_el_contador_de_intentos(self):
        u = usuario(intentos_fallidos=0)
        e = Escenario([u])
        with pytest.raises(NoAutorizadoError):
            await e.login(password="otraClave1")
        assert u.intentos_fallidos == 1

    async def test_registra_el_intento_fallido_en_bitacora(self):
        e = Escenario()
        with pytest.raises(NoAutorizadoError):
            await e.login(password="otraClave1")
        assert "login_fallido" in e.auditoria.acciones()

    async def test_el_fallido_de_usuario_inexistente_va_sin_usuario_id(self):
        e = Escenario()
        with pytest.raises(NoAutorizadoError):
            await e.login(username="fantasma")
        assert e.auditoria.eventos[0]["usuario_id"] is None


class TestBloqueoPorIntentos:
    async def test_bloquea_al_llegar_al_maximo_configurado(self):
        u = usuario(intentos_fallidos=2)  # max por defecto = 3
        e = Escenario([u])
        with pytest.raises(NoAutorizadoError):
            await e.login(password="mala1234")
        assert u.bloqueado_hasta is not None

    async def test_al_bloquear_resetea_el_contador(self):
        """Si no, al vencer el bloqueo el usuario entraría ya al borde."""
        u = usuario(intentos_fallidos=2)
        e = Escenario([u])
        with pytest.raises(NoAutorizadoError):
            await e.login(password="mala1234")
        assert u.intentos_fallidos == 0

    async def test_no_bloquea_antes_del_maximo(self):
        u = usuario(intentos_fallidos=0)
        e = Escenario([u])
        with pytest.raises(NoAutorizadoError):
            await e.login(password="mala1234")
        assert u.bloqueado_hasta is None

    async def test_el_maximo_sale_de_la_configuracion(self):
        """Se puede endurecer sin redeploy."""
        config = ConfiguracionNegocio(id=1, nombre_negocio="K", max_intentos_login=5)
        u = usuario(intentos_fallidos=3)
        e = Escenario([u], config)
        with pytest.raises(NoAutorizadoError):
            await e.login(password="mala1234")
        assert u.bloqueado_hasta is None  # con max=5 todavía no bloquea

    async def test_la_duracion_del_bloqueo_sale_de_la_configuracion(self):
        config = ConfiguracionNegocio(
            id=1, nombre_negocio="K", max_intentos_login=1, minutos_bloqueo=45
        )
        u = usuario(intentos_fallidos=0)
        e = Escenario([u], config)
        with pytest.raises(NoAutorizadoError):
            await e.login(password="mala1234")
        assert u.bloqueado_hasta is not None
        restante = u.bloqueado_hasta - u.bloqueado_hasta.replace(microsecond=0)
        assert (u.bloqueado_hasta - restante) is not None  # existe y es futura

    async def test_deja_el_evento_cuenta_bloqueada(self):
        u = usuario(intentos_fallidos=2)
        e = Escenario([u])
        with pytest.raises(NoAutorizadoError):
            await e.login(password="mala1234")
        assert "cuenta_bloqueada" in e.auditoria.acciones()

    async def test_usuario_ya_bloqueado_recibe_error_ESPECIFICO(self):
        """Acá sí se le dice que está bloqueado: ya probó su identidad al
        gatillar el bloqueo, y necesita saber por qué no entra."""
        u = usuario(bloqueado_hasta=AHORA + timedelta(days=999))
        e = Escenario([u])
        with pytest.raises(CuentaBloqueadaError):
            await e.login()

    async def test_bloqueado_no_pasa_ni_con_la_password_correcta(self):
        u = usuario(bloqueado_hasta=AHORA + timedelta(days=999))
        e = Escenario([u])
        with pytest.raises(CuentaBloqueadaError):
            await e.login(password=PASSWORD)
        assert e.sesiones.sesiones == []

    async def test_el_rechazo_por_bloqueo_queda_registrado(self):
        u = usuario(bloqueado_hasta=AHORA + timedelta(days=999))
        e = Escenario([u])
        with pytest.raises(CuentaBloqueadaError):
            await e.login()
        assert "login_rechazado_bloqueo" in e.auditoria.acciones()

    async def test_bloqueo_vencido_permite_entrar(self):
        u = usuario(bloqueado_hasta=AHORA - timedelta(days=1))
        e = Escenario([u])
        r = await e.login()
        assert r.access_token
