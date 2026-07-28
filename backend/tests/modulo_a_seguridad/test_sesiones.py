"""Ciclo de vida de la sesión: renovación (`refresh`) y cierre (`logout`).

La regla central del refresh es la **rotación**: cada renovación mata la sesión
anterior y emite una nueva. Si el refresh viejo siguiera sirviendo, robarlo una
vez daría acceso para siempre.
"""

from datetime import timedelta

import pytest

from app.modules.modulo_a_seguridad.application.logout_usecase import LogoutUseCase
from app.modules.modulo_a_seguridad.application.refresh_token_usecase import (
    RefreshTokenUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import SesionToken
from app.shared.kernel.exceptions import NoAutorizadoError

from .dobles import (
    AHORA,
    AuditoriaFake,
    ConfiguracionRepoFake,
    SesionRepoFake,
    TokenServiceFake,
    UsuarioRepoFake,
    usuario,
)


class EscenarioRefresh:
    def __init__(self, usuarios=None):
        self.usuarios = UsuarioRepoFake(usuarios if usuarios is not None else [usuario()])
        self.sesiones = SesionRepoFake()
        self.config = ConfiguracionRepoFake()
        self.tokens = TokenServiceFake()
        self.caso = RefreshTokenUseCase(
            self.usuarios, self.sesiones, self.config, self.tokens
        )

    async def con_sesion_vigente(self, refresh="refresh-original", usuario_id=1):
        """Deja una sesión válida ya guardada y devuelve el refresh en claro."""
        from datetime import datetime, timezone

        await self.sesiones.crear(
            SesionToken(
                id=None,
                usuario_id=usuario_id,
                refresh_token_hash=self.tokens.hashear_refresh_token(refresh),
                ip="1.2.3.4",
                user_agent="tests",
                expira_en=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        return refresh

    async def refrescar(self, token):
        return await self.caso.ejecutar(
            refresh_token=token, ip="1.2.3.4", user_agent="tests"
        )


class TestRefreshExitoso:
    async def test_devuelve_tokens_nuevos(self):
        e = EscenarioRefresh()
        viejo = await e.con_sesion_vigente()
        r = await e.refrescar(viejo)
        assert r.access_token
        assert r.refresh_token != viejo

    async def test_revoca_la_sesion_anterior(self):
        """Rotación: el refresh usado no puede volver a servir."""
        e = EscenarioRefresh()
        viejo = await e.con_sesion_vigente()
        await e.refrescar(viejo)
        assert e.sesiones.sesiones[0].revocada is True

    async def test_crea_una_sesion_nueva(self):
        e = EscenarioRefresh()
        viejo = await e.con_sesion_vigente()
        await e.refrescar(viejo)
        assert len(e.sesiones.sesiones) == 2
        assert e.sesiones.sesiones[1].revocada is False

    async def test_el_refresh_viejo_ya_no_sirve(self):
        e = EscenarioRefresh()
        viejo = await e.con_sesion_vigente()
        await e.refrescar(viejo)
        with pytest.raises(NoAutorizadoError):
            await e.refrescar(viejo)

    async def test_guarda_el_hash_del_nuevo_refresh_no_el_token(self):
        e = EscenarioRefresh()
        r = await e.refrescar(await e.con_sesion_vigente())
        nueva = e.sesiones.sesiones[1]
        assert nueva.refresh_token_hash != r.refresh_token

    async def test_la_sesion_nueva_toma_el_ttl_del_rol(self):
        e = EscenarioRefresh([usuario(rol_nombre="ADMIN")])
        await e.refrescar(await e.con_sesion_vigente())
        nueva = e.sesiones.sesiones[1]
        assert nueva.expira_en > e.sesiones.sesiones[0].expira_en


class TestRefreshRechazado:
    async def test_token_desconocido(self):
        e = EscenarioRefresh()
        with pytest.raises(NoAutorizadoError):
            await e.refrescar("inventado")

    async def test_sesion_revocada(self):
        e = EscenarioRefresh()
        viejo = await e.con_sesion_vigente()
        e.sesiones.sesiones[0].revocada = True
        with pytest.raises(NoAutorizadoError):
            await e.refrescar(viejo)

    async def test_sesion_expirada(self):
        from datetime import datetime, timezone

        e = EscenarioRefresh()
        viejo = await e.con_sesion_vigente()
        e.sesiones.sesiones[0].expira_en = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )
        with pytest.raises(NoAutorizadoError):
            await e.refrescar(viejo)

    async def test_usuario_desactivado_despues_de_loguearse(self):
        """La sesión sigue vigente pero el usuario ya no puede entrar: el
        refresh es el punto donde se corta el acceso."""
        u = usuario(activo=False)
        e = EscenarioRefresh([u])
        with pytest.raises(NoAutorizadoError):
            await e.refrescar(await e.con_sesion_vigente())

    async def test_usuario_eliminado(self):
        e = EscenarioRefresh([usuario(deleted_at=AHORA)])
        with pytest.raises(NoAutorizadoError):
            await e.refrescar(await e.con_sesion_vigente())

    async def test_usuario_inexistente(self):
        e = EscenarioRefresh([])
        with pytest.raises(NoAutorizadoError):
            await e.refrescar(await e.con_sesion_vigente(usuario_id=999))

    async def test_el_mensaje_no_distingue_el_motivo(self):
        """Todos los rechazos dicen lo mismo: no se filtra si el token existía,
        si venció o si el usuario fue dado de baja."""
        e = EscenarioRefresh()
        with pytest.raises(NoAutorizadoError) as desconocido:
            await e.refrescar("inventado")
        e2 = EscenarioRefresh([usuario(activo=False)])
        with pytest.raises(NoAutorizadoError) as inactivo:
            await e2.refrescar(await e2.con_sesion_vigente())
        assert str(desconocido.value) == str(inactivo.value)

    async def test_no_crea_sesion_cuando_rechaza(self):
        e = EscenarioRefresh()
        with pytest.raises(NoAutorizadoError):
            await e.refrescar("inventado")
        assert e.sesiones.sesiones == []


class TestLogout:
    def _caso(self):
        sesiones = SesionRepoFake()
        auditoria = AuditoriaFake()
        tokens = TokenServiceFake()
        return LogoutUseCase(sesiones, tokens, auditoria), sesiones, auditoria, tokens

    async def test_revoca_la_sesion_del_token_entregado(self):
        caso, sesiones, _, tokens = self._caso()
        from datetime import datetime, timezone

        await sesiones.crear(
            SesionToken(
                id=None,
                usuario_id=1,
                refresh_token_hash=tokens.hashear_refresh_token("mi-refresh"),
                ip="",
                user_agent="",
                expira_en=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        await caso.ejecutar(
            usuario=usuario(), refresh_token="mi-refresh", ip="", user_agent=""
        )
        assert sesiones.sesiones[0].revocada is True

    async def test_token_inexistente_no_revienta(self):
        """Cerrar sesión con un token ya vencido tiene que ser inofensivo: el
        usuario igual queda deslogueado del lado del cliente."""
        caso, _, _, _ = self._caso()
        await caso.ejecutar(
            usuario=usuario(), refresh_token="inventado", ip="", user_agent=""
        )

    async def test_deja_rastro_en_bitacora(self):
        caso, _, auditoria, _ = self._caso()
        await caso.ejecutar(
            usuario=usuario(), refresh_token="x", ip="", user_agent=""
        )
        assert auditoria.eventos, "el logout debe quedar registrado"
