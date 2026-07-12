# Dependencias de FastAPI del módulo de seguridad.
# ⭐ CONTRATO PÚBLICO DEL MÓDULO A: los módulos B, C y D importan DESDE AQUÍ
# (y solo desde aquí) para proteger sus endpoints y auditar sus operaciones.
# Guía de uso: docs/API_MODULO_A.md.
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_permiso_repository import (
    SqlAlchemyPermisoRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_usuario_repository import (
    SqlAlchemyUsuarioRepository,
)
from app.shared.database.session import get_db
from app.shared.kernel.exceptions import NoAutorizadoError, ProhibidoError

_esquema_bearer = HTTPBearer(auto_error=False)


def contexto_request(request: Request) -> tuple[str, str]:
    """(ip, user_agent) del request, para la bitácora."""
    ip = request.client.host if request.client else ""
    return ip, request.headers.get("user-agent", "")


async def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Valida el JWT y devuelve el usuario ACTUAL desde BD (garantiza que sigue activo).

    Uso en cualquier módulo:
        @router.get("/productos")
        async def listar(usuario: Usuario = Depends(get_current_user)): ...
    """
    if credenciales is None:
        raise NoAutorizadoError("Falta el token de autenticación.")
    claims = module_container.token_service.decodificar_access_token(credenciales.credentials)
    usuario = await SqlAlchemyUsuarioRepository(db).buscar_por_id(int(claims["sub"]))
    if usuario is None or not usuario.puede_iniciar_sesion():
        raise NoAutorizadoError("Sesión inválida. Inicia sesión de nuevo.")
    return usuario


def require_role(nombre_rol: str):
    """Exige un rol exacto. Uso:  Depends(require_role("ADMIN"))"""

    async def _verificar(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol_nombre != nombre_rol:
            raise ProhibidoError("No tienes permisos para realizar esta acción.")
        return usuario

    return _verificar


def require_permission(codigo_permiso: str):
    """Exige un permiso (consultado en BD: cambia sin redeploy y sin re-login).

    Uso en cualquier módulo:
        @router.post("/ventas/anular")
        async def anular(usuario: Usuario = Depends(require_permission("ventas.anular"))): ...
    """

    async def _verificar(
        usuario: Usuario = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Usuario:
        if not await SqlAlchemyPermisoRepository(db).rol_tiene_permiso(usuario.rol_id, codigo_permiso):
            raise ProhibidoError("No tienes permisos para realizar esta acción.")
        return usuario

    return _verificar


def get_auditoria(db: AsyncSession = Depends(get_db)) -> RegistrarAuditoriaUseCase:
    """Servicio de auditoría listo para usar desde los módulos B, C y D.

    Uso:
        @router.post("/ventas")
        async def registrar_venta(..., auditoria = Depends(get_auditoria)):
            await auditoria.ejecutar(accion="venta_registrada", entidad="ventas", ...)
    """
    return module_container.auditoria_usecase(db)
