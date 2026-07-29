"""Dobles en memoria de los puertos del Módulo A.

Implementan el contrato real (mismos nombres y firmas que los puertos), pero
guardando en listas. Así los tests de casos de uso corren sin BD y fallan
cuando cambia el contrato, que es justamente lo que queremos que detecten.

Además registran lo que reciben (`eventos`, `confirmaciones`) para poder
afirmar sobre EFECTOS y no sólo sobre el valor devuelto.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.modulo_a_seguridad.domain.entities import (
    ConfiguracionNegocio,
    Permiso,
    Rol,
    SesionToken,
    Usuario,
)


class UsuarioRepoFake:
    def __init__(self, usuarios: list[Usuario] | None = None):
        self.usuarios = list(usuarios or [])
        self.actualizados: list[Usuario] = []
        self._siguiente_id = 100

    async def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        return next(
            (u for u in self.usuarios if u.id == usuario_id and not u.eliminado), None
        )

    async def buscar_por_username(self, username: str) -> Usuario | None:
        return next((u for u in self.usuarios if u.username == username), None)

    async def listar(self, incluir_inactivos: bool = False) -> list[Usuario]:
        return [u for u in self.usuarios if incluir_inactivos or u.activo]

    async def crear(self, usuario: Usuario) -> Usuario:
        usuario.id = self._siguiente_id
        self._siguiente_id += 1
        self.usuarios.append(usuario)
        return usuario

    async def actualizar(self, usuario: Usuario) -> Usuario:
        self.actualizados.append(usuario)
        return usuario

    async def existe_username(self, username: str) -> bool:
        return any(u.username == username for u in self.usuarios)


class SesionRepoFake:
    def __init__(self):
        self.sesiones: list[SesionToken] = []
        self.revocadas: list[int] = []
        self.revocadas_de_usuario: list[int] = []

    async def crear(self, sesion: SesionToken) -> SesionToken:
        sesion.id = len(self.sesiones) + 1
        self.sesiones.append(sesion)
        return sesion

    async def buscar_por_hash(self, token_hash: str) -> SesionToken | None:
        return next(
            (s for s in self.sesiones if s.refresh_token_hash == token_hash), None
        )

    async def revocar(self, sesion_id: int) -> None:
        # El puerto revoca por ID, no por hash (ver `SesionRepositoryPort`).
        self.revocadas.append(sesion_id)
        for s in self.sesiones:
            if s.id == sesion_id:
                s.revocada = True

    async def revocar_todas_de_usuario(self, usuario_id: int) -> None:
        self.revocadas_de_usuario.append(usuario_id)
        for s in self.sesiones:
            if s.usuario_id == usuario_id:
                s.revocada = True


class ConfiguracionRepoFake:
    def __init__(self, config: ConfiguracionNegocio | None = None):
        self.config = config or ConfiguracionNegocio(id=1, nombre_negocio="Kiosco")

    async def obtener(self) -> ConfiguracionNegocio:
        return self.config

    async def actualizar(self, config: ConfiguracionNegocio) -> ConfiguracionNegocio:
        self.config = config
        return config


class HasherFake:
    """Hash simulado: `hash(x) == "h:" + x`. Determinista y legible en los fallos."""

    def hashear(self, password: str) -> str:
        return f"h:{password}"

    def verificar(self, password: str, password_hash: str) -> bool:
        return password_hash == f"h:{password}"


class TokenServiceFake:
    def __init__(self):
        self.access_tokens_creados: list[tuple] = []
        self._contador = 0

    def crear_access_token(self, usuario_id, username, rol) -> str:
        self.access_tokens_creados.append((usuario_id, username, rol))
        return f"access-{usuario_id}"

    def generar_refresh_token(self) -> str:
        self._contador += 1
        return f"refresh-{self._contador}"

    def hashear_refresh_token(self, token: str) -> str:
        return f"h:{token}"

    def decodificar_access_token(self, token: str) -> dict:
        return {"sub": token.replace("access-", "")}


class AuditoriaFake:
    """Sustituye a `RegistrarAuditoriaUseCase`: guarda los eventos recibidos."""

    def __init__(self):
        self.eventos: list[dict] = []

    async def ejecutar(self, **kwargs):
        self.eventos.append(kwargs)

    def acciones(self) -> list[str]:
        return [e.get("accion") for e in self.eventos]


class UnidadTrabajoFake:
    def __init__(self):
        self.confirmaciones = 0
        self.reversiones = 0

    async def confirmar(self) -> None:
        self.confirmaciones += 1

    async def revertir(self) -> None:
        self.reversiones += 1


class PermisoRepoFake:
    """Sigue la firma real de `PermisoRepositoryPort`."""

    def __init__(self, por_rol: dict[int, list[str]] | None = None):
        self.por_rol = por_rol or {}
        self.reemplazos: list[tuple[int, list[str]]] = []

    def _permiso(self, codigo: str) -> Permiso:
        return Permiso(id=abs(hash(codigo)) % 10_000, codigo=codigo)

    async def listar_roles(self) -> list[Rol]:
        return [Rol(id=1, nombre="ADMIN"), Rol(id=2, nombre="CAJERO")]

    async def listar_permisos(self) -> list[Permiso]:
        todos = sorted({c for cs in self.por_rol.values() for c in cs})
        return [self._permiso(c) for c in todos]

    async def permisos_de_rol(self, rol_id: int) -> list[Permiso]:
        return [self._permiso(c) for c in self.por_rol.get(rol_id, [])]

    async def rol_tiene_permiso(self, rol_id: int, codigo_permiso: str) -> bool:
        return codigo_permiso in self.por_rol.get(rol_id, [])

    async def reemplazar_permisos_de_rol(
        self, rol_id: int, codigos: list[str]
    ) -> list[Permiso]:
        self.reemplazos.append((rol_id, list(codigos)))
        self.por_rol[rol_id] = list(codigos)
        return [self._permiso(c) for c in codigos]


def usuario(**kwargs) -> Usuario:
    """Usuario válido por defecto; se sobreescribe lo que interese al test."""
    base = dict(
        id=1,
        username="cajero1",
        nombre="Ana Torres",
        password_hash="h:Clave123",
        rol_id=2,
        rol_nombre="CAJERO",
        activo=True,
    )
    base.update(kwargs)
    return Usuario(**base)  # type: ignore[arg-type]


AHORA = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)
