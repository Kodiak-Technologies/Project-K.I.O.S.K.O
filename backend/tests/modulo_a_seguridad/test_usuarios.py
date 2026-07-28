"""Gestión de usuarios: alta, edición, baja, contraseñas y permisos.

Todo lo que hay acá lo ejecuta un ADMIN sobre otra cuenta. Las reglas que más
importan son las que evitan que se dispare en el pie (no puede desactivarse ni
eliminarse a sí mismo) y las que cierran las sesiones cuando una cuenta deja de
tener acceso.
"""

import pytest

from app.modules.modulo_a_seguridad.application.asignar_permisos_usecase import (
    AsignarPermisosUseCase,
)
from app.modules.modulo_a_seguridad.application.cambiar_password_usecase import (
    CambiarPasswordUseCase,
)
from app.modules.modulo_a_seguridad.application.crear_usuario_usecase import (
    CrearUsuarioUseCase,
)
from app.modules.modulo_a_seguridad.application.desactivar_usuario_usecase import (
    CambiarEstadoUsuarioUseCase,
)
from app.modules.modulo_a_seguridad.application.editar_usuario_usecase import (
    EditarUsuarioUseCase,
)
from app.modules.modulo_a_seguridad.application.eliminar_usuario_usecase import (
    EliminarUsuarioUseCase,
)
from app.modules.modulo_a_seguridad.application.resetear_password_usecase import (
    ResetearPasswordUseCase,
)
from app.shared.kernel.exceptions import (
    ConflictoError,
    NoAutorizadoError,
    NoEncontradoError,
    ValidacionError,
)

from .dobles import (
    AuditoriaFake,
    HasherFake,
    PermisoRepoFake,
    SesionRepoFake,
    UsuarioRepoFake,
    usuario,
)

ADMIN = usuario(id=99, username="admin", rol_id=1, rol_nombre="ADMIN")
CTX = dict(ip="1.2.3.4", user_agent="tests")


class TestCrearUsuario:
    def _caso(self, existentes=None):
        repo = UsuarioRepoFake(existentes or [])
        aud = AuditoriaFake()
        return CrearUsuarioUseCase(repo, HasherFake(), aud), repo, aud

    async def test_crea_con_password_hasheada(self):
        caso, repo, _ = self._caso()
        u = await caso.ejecutar(
            admin=ADMIN, username="nuevo1", nombre="Nuevo", password_inicial="Clave123",
            rol_id=2, forzar_cambio_password=True, **CTX,
        )
        assert u.id is not None
        assert u.password_hash != "Clave123", "la contraseña no puede guardarse en claro"
        assert u.password_hash == "h:Clave123"

    async def test_nace_activo(self):
        caso, _, _ = self._caso()
        u = await caso.ejecutar(
            admin=ADMIN, username="nuevo1", nombre="N", password_inicial="Clave123",
            rol_id=2, forzar_cambio_password=False, **CTX,
        )
        assert u.activo is True

    @pytest.mark.parametrize("forzar", [True, False])
    async def test_respeta_el_flag_de_cambio_obligatorio(self, forzar):
        caso, _, _ = self._caso()
        u = await caso.ejecutar(
            admin=ADMIN, username="nuevo1", nombre="N", password_inicial="Clave123",
            rol_id=2, forzar_cambio_password=forzar, **CTX,
        )
        assert u.debe_cambiar_password is forzar

    async def test_rechaza_username_duplicado(self):
        caso, _, _ = self._caso([usuario(username="repetido")])
        with pytest.raises(ConflictoError):
            await caso.ejecutar(
                admin=ADMIN, username="repetido", nombre="N",
                password_inicial="Clave123", rol_id=2,
                forzar_cambio_password=False, **CTX,
            )

    async def test_valida_el_formato_del_username(self):
        caso, _, _ = self._caso()
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                admin=ADMIN, username="MAYUSCULAS", nombre="N",
                password_inicial="Clave123", rol_id=2,
                forzar_cambio_password=False, **CTX,
            )

    async def test_valida_la_politica_de_password(self):
        caso, _, _ = self._caso()
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                admin=ADMIN, username="nuevo1", nombre="N",
                password_inicial="corta", rol_id=2,
                forzar_cambio_password=False, **CTX,
            )

    async def test_no_crea_nada_si_falla_la_validacion(self):
        caso, repo, _ = self._caso()
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                admin=ADMIN, username="X", nombre="N", password_inicial="Clave123",
                rol_id=2, forzar_cambio_password=False, **CTX,
            )
        assert repo.usuarios == []

    async def test_registra_quien_lo_creo(self):
        caso, _, aud = self._caso()
        await caso.ejecutar(
            admin=ADMIN, username="nuevo1", nombre="N", password_inicial="Clave123",
            rol_id=2, forzar_cambio_password=False, **CTX,
        )
        evento = aud.eventos[0]
        assert evento["accion"] == "usuario_creado"
        assert evento["usuario_id"] == ADMIN.id
        assert "password" not in str(evento), "la contraseña no debe filtrarse a bitácora"


class TestEditarUsuario:
    def _caso(self, existentes):
        repo = UsuarioRepoFake(existentes)
        aud = AuditoriaFake()
        return EditarUsuarioUseCase(repo, aud), repo, aud

    async def test_cambia_nombre_y_rol(self):
        u = usuario(id=5, nombre="Viejo", rol_id=2)
        caso, _, _ = self._caso([u])
        r = await caso.ejecutar(
            admin=ADMIN, usuario_id=5, nombre="Nuevo", rol_id=1, **CTX
        )
        assert r.nombre == "Nuevo" and r.rol_id == 1

    async def test_los_campos_en_None_no_se_tocan(self):
        u = usuario(id=5, nombre="Original", rol_id=2)
        caso, _, _ = self._caso([u])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, nombre=None, rol_id=None, **CTX)
        assert u.nombre == "Original" and u.rol_id == 2

    async def test_usuario_inexistente(self):
        caso, _, _ = self._caso([])
        with pytest.raises(NoEncontradoError):
            await caso.ejecutar(
                admin=ADMIN, usuario_id=404, nombre="X", rol_id=None, **CTX
            )

    async def test_guarda_el_valor_anterior_en_bitacora(self):
        """Sin el 'antes' la bitácora no sirve para auditar."""
        u = usuario(id=5, nombre="Viejo", rol_id=2)
        caso, _, aud = self._caso([u])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, nombre="Nuevo", rol_id=1, **CTX)
        e = aud.eventos[0]
        assert e["valor_anterior"] == {"nombre": "Viejo", "rol_id": 2}
        assert e["valor_nuevo"] == {"nombre": "Nuevo", "rol_id": 1}


class TestCambiarEstado:
    def _caso(self, existentes):
        repo = UsuarioRepoFake(existentes)
        ses = SesionRepoFake()
        aud = AuditoriaFake()
        return CambiarEstadoUsuarioUseCase(repo, ses, aud), ses, aud

    async def test_desactivar_cierra_todas_sus_sesiones(self):
        """Si no, el desactivado sigue operando hasta que venza su token."""
        caso, ses, _ = self._caso([usuario(id=5)])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, activo=False, **CTX)
        assert ses.revocadas_de_usuario == [5]

    async def test_reactivar_no_toca_sesiones(self):
        caso, ses, _ = self._caso([usuario(id=5, activo=False)])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, activo=True, **CTX)
        assert ses.revocadas_de_usuario == []

    async def test_el_admin_no_puede_desactivarse_a_si_mismo(self):
        caso, _, _ = self._caso([ADMIN])
        with pytest.raises(ValidacionError):
            await caso.ejecutar(admin=ADMIN, usuario_id=ADMIN.id, activo=False, **CTX)

    async def test_pero_si_puede_reactivarse(self):
        caso, _, _ = self._caso([ADMIN])
        await caso.ejecutar(admin=ADMIN, usuario_id=ADMIN.id, activo=True, **CTX)

    async def test_usuario_inexistente(self):
        caso, _, _ = self._caso([])
        with pytest.raises(NoEncontradoError):
            await caso.ejecutar(admin=ADMIN, usuario_id=404, activo=False, **CTX)

    @pytest.mark.parametrize(
        "activo,accion", [(True, "usuario_activado"), (False, "usuario_desactivado")]
    )
    async def test_la_accion_registrada_distingue_alta_de_baja(self, activo, accion):
        caso, _, aud = self._caso([usuario(id=5, activo=not activo)])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, activo=activo, **CTX)
        assert aud.acciones() == [accion]


class TestEliminarUsuario:
    def _caso(self, existentes):
        repo = UsuarioRepoFake(existentes)
        ses = SesionRepoFake()
        aud = AuditoriaFake()
        return EliminarUsuarioUseCase(repo, ses, aud), ses, aud

    async def test_es_baja_logica_no_fisica(self):
        u = usuario(id=5)
        caso, _, _ = self._caso([u])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, motivo="renuncia", **CTX)
        assert u.deleted_at is not None
        assert u.deleted_by == ADMIN.id
        assert u.activo is False

    async def test_cierra_sus_sesiones(self):
        caso, ses, _ = self._caso([usuario(id=5)])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, motivo=None, **CTX)
        assert ses.revocadas_de_usuario == [5]

    async def test_el_admin_no_puede_eliminarse_a_si_mismo(self):
        caso, _, _ = self._caso([ADMIN])
        with pytest.raises(ValidacionError):
            await caso.ejecutar(admin=ADMIN, usuario_id=ADMIN.id, motivo=None, **CTX)

    async def test_no_se_puede_eliminar_dos_veces(self):
        from datetime import datetime, timezone

        caso, _, _ = self._caso([usuario(id=5, deleted_at=datetime.now(timezone.utc))])
        with pytest.raises(NoEncontradoError):
            await caso.ejecutar(admin=ADMIN, usuario_id=5, motivo=None, **CTX)

    async def test_el_motivo_queda_registrado(self):
        caso, _, aud = self._caso([usuario(id=5)])
        await caso.ejecutar(admin=ADMIN, usuario_id=5, motivo="dejó el puesto", **CTX)
        assert aud.eventos[0]["motivo"] == "dejó el puesto"


class TestCambiarPasswordPropia:
    def _caso(self, u):
        repo = UsuarioRepoFake([u])
        aud = AuditoriaFake()
        return CambiarPasswordUseCase(repo, HasherFake(), aud), aud

    async def test_cambia_la_password(self):
        u = usuario(password_hash="h:Vieja123")
        caso, _ = self._caso(u)
        await caso.ejecutar(
            usuario=u, password_actual="Vieja123", password_nueva="Nueva123", **CTX
        )
        assert u.password_hash == "h:Nueva123"

    async def test_exige_la_password_actual_correcta(self):
        u = usuario(password_hash="h:Vieja123")
        caso, _ = self._caso(u)
        with pytest.raises(NoAutorizadoError):
            await caso.ejecutar(
                usuario=u, password_actual="Equivocada1", password_nueva="Nueva123", **CTX
            )
        assert u.password_hash == "h:Vieja123", "no debe cambiar si falló la verificación"

    async def test_valida_la_politica_de_la_nueva(self):
        u = usuario(password_hash="h:Vieja123")
        caso, _ = self._caso(u)
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                usuario=u, password_actual="Vieja123", password_nueva="corta", **CTX
            )

    async def test_limpia_el_flag_de_cambio_obligatorio(self):
        u = usuario(password_hash="h:Vieja123", debe_cambiar_password=True)
        caso, _ = self._caso(u)
        await caso.ejecutar(
            usuario=u, password_actual="Vieja123", password_nueva="Nueva123", **CTX
        )
        assert u.debe_cambiar_password is False


class TestResetearPassword:
    def _caso(self, existentes):
        repo = UsuarioRepoFake(existentes)
        ses = SesionRepoFake()
        aud = AuditoriaFake()
        return ResetearPasswordUseCase(repo, ses, HasherFake(), aud), ses, aud

    async def test_el_admin_no_necesita_la_password_anterior(self):
        u = usuario(id=5, password_hash="h:LaQueSea1")
        caso, _, _ = self._caso([u])
        await caso.ejecutar(
            admin=ADMIN, usuario_id=5, password_nueva="Nueva123",
            forzar_cambio=True, **CTX,
        )
        assert u.password_hash == "h:Nueva123"

    async def test_desbloquea_la_cuenta(self):
        """Resetear la contraseña es también la vía para destrabar a alguien
        que se bloqueó por intentos fallidos."""
        u = usuario(id=5, intentos_fallidos=3)
        caso, _, _ = self._caso([u])
        await caso.ejecutar(
            admin=ADMIN, usuario_id=5, password_nueva="Nueva123",
            forzar_cambio=False, **CTX,
        )
        assert u.intentos_fallidos == 0

    async def test_valida_la_politica(self):
        caso, _, _ = self._caso([usuario(id=5)])
        with pytest.raises(ValidacionError):
            await caso.ejecutar(
                admin=ADMIN, usuario_id=5, password_nueva="abc",
                forzar_cambio=False, **CTX,
            )

    async def test_usuario_inexistente(self):
        caso, _, _ = self._caso([])
        with pytest.raises(NoEncontradoError):
            await caso.ejecutar(
                admin=ADMIN, usuario_id=404, password_nueva="Nueva123",
                forzar_cambio=False, **CTX,
            )


class TestAsignarPermisos:
    def _caso(self, por_rol=None):
        repo = PermisoRepoFake(por_rol or {})
        aud = AuditoriaFake()
        return AsignarPermisosUseCase(repo, aud), repo, aud

    async def test_reemplaza_el_set_completo(self):
        """No es 'agregar': lo que no viene en la lista se quita."""
        caso, repo, _ = self._caso({2: ["ventas.registrar", "caja.abrir_turno"]})
        await caso.ejecutar(admin=ADMIN, rol_id=2, codigos=["ventas.registrar"], **CTX)
        assert repo.por_rol[2] == ["ventas.registrar"]

    async def test_lista_vacia_deja_al_rol_sin_permisos(self):
        caso, repo, _ = self._caso({2: ["ventas.registrar"]})
        await caso.ejecutar(admin=ADMIN, rol_id=2, codigos=[], **CTX)
        assert repo.por_rol[2] == []

    async def test_registra_el_antes_y_el_despues(self):
        caso, _, aud = self._caso({2: ["viejo.permiso"]})
        await caso.ejecutar(admin=ADMIN, rol_id=2, codigos=["nuevo.permiso"], **CTX)
        e = aud.eventos[0]
        assert e["valor_anterior"] == {"permisos": ["viejo.permiso"]}
        assert e["valor_nuevo"] == {"permisos": ["nuevo.permiso"]}
