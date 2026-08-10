# Wiring del módulo: el ÚNICO lugar donde se conectan casos de uso con adaptadores
# concretos. Los routers piden estas piezas ya armadas vía Depends (ver infrastructure/dependencies.py).
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.application.actualizar_configuracion_usecase import (
    ActualizarConfiguracionUseCase,
)
from app.modules.modulo_a_seguridad.application.asignar_permisos_usecase import (
    AsignarPermisosUseCase,
)
from app.modules.modulo_a_seguridad.application.cambiar_password_usecase import (
    CambiarPasswordUseCase,
)
from app.modules.modulo_a_seguridad.application.consultar_bitacora_usecase import (
    ConsultarBitacoraUseCase,
)
from app.modules.modulo_a_seguridad.application.crear_usuario_usecase import CrearUsuarioUseCase
from app.modules.modulo_a_seguridad.application.desactivar_usuario_usecase import (
    CambiarEstadoUsuarioUseCase,
)
from app.modules.modulo_a_seguridad.application.editar_usuario_usecase import EditarUsuarioUseCase
from app.modules.modulo_a_seguridad.application.eliminar_usuario_usecase import (
    EliminarUsuarioUseCase,
)
from app.modules.modulo_a_seguridad.application.login_usecase import LoginUseCase
from app.modules.modulo_a_seguridad.application.logout_usecase import LogoutUseCase
from app.modules.modulo_a_seguridad.application.refresh_token_usecase import RefreshTokenUseCase
from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.application.resetear_password_usecase import (
    ResetearPasswordUseCase,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_auditoria_repository import (
    SqlAlchemyAuditoriaRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_configuracion_repository import (
    SqlAlchemyConfiguracionRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_permiso_repository import (
    SqlAlchemyPermisoRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_sesion_repository import (
    SqlAlchemySesionRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_unidad_trabajo import (
    SqlAlchemyUnidadTrabajo,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_usuario_repository import (
    SqlAlchemyUsuarioRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)
from app.modules.modulo_a_seguridad.infrastructure.adapters.security.jwt_token_service import (
    JwtTokenService,
)

# Adaptadores sin estado: una sola instancia basta.
hasher = BcryptPasswordHasher()
token_service = JwtTokenService()


def auditoria_usecase(db: AsyncSession) -> RegistrarAuditoriaUseCase:
    return RegistrarAuditoriaUseCase(SqlAlchemyAuditoriaRepository(db))


def configuracion_repository(db: AsyncSession) -> SqlAlchemyConfiguracionRepository:
    """Expuesto para otros módulos que necesiten leer la configuración del negocio."""
    return SqlAlchemyConfiguracionRepository(db)


def login_usecase(db: AsyncSession) -> LoginUseCase:
    return LoginUseCase(
        SqlAlchemyUsuarioRepository(db),
        SqlAlchemySesionRepository(db),
        SqlAlchemyConfiguracionRepository(db),
        hasher,
        token_service,
        auditoria_usecase(db),
        SqlAlchemyUnidadTrabajo(db),
    )


def refresh_usecase(db: AsyncSession) -> RefreshTokenUseCase:
    return RefreshTokenUseCase(
        SqlAlchemyUsuarioRepository(db),
        SqlAlchemySesionRepository(db),
        SqlAlchemyConfiguracionRepository(db),
        token_service,
    )


def logout_usecase(db: AsyncSession) -> LogoutUseCase:
    return LogoutUseCase(SqlAlchemySesionRepository(db), token_service, auditoria_usecase(db))


def cambiar_password_usecase(db: AsyncSession) -> CambiarPasswordUseCase:
    return CambiarPasswordUseCase(SqlAlchemyUsuarioRepository(db), hasher, auditoria_usecase(db))


def crear_usuario_usecase(db: AsyncSession) -> CrearUsuarioUseCase:
    return CrearUsuarioUseCase(SqlAlchemyUsuarioRepository(db), hasher, auditoria_usecase(db))


def editar_usuario_usecase(db: AsyncSession) -> EditarUsuarioUseCase:
    return EditarUsuarioUseCase(SqlAlchemyUsuarioRepository(db), auditoria_usecase(db))


def cambiar_estado_usuario_usecase(db: AsyncSession) -> CambiarEstadoUsuarioUseCase:
    return CambiarEstadoUsuarioUseCase(
        SqlAlchemyUsuarioRepository(db), SqlAlchemySesionRepository(db), auditoria_usecase(db)
    )


def eliminar_usuario_usecase(db: AsyncSession) -> EliminarUsuarioUseCase:
    return EliminarUsuarioUseCase(
        SqlAlchemyUsuarioRepository(db), SqlAlchemySesionRepository(db), auditoria_usecase(db)
    )


def resetear_password_usecase(db: AsyncSession) -> ResetearPasswordUseCase:
    return ResetearPasswordUseCase(
        SqlAlchemyUsuarioRepository(db),
        SqlAlchemySesionRepository(db),
        hasher,
        auditoria_usecase(db),
    )


def consultar_bitacora_usecase(db: AsyncSession) -> ConsultarBitacoraUseCase:
    return ConsultarBitacoraUseCase(SqlAlchemyAuditoriaRepository(db))


def actualizar_configuracion_usecase(db: AsyncSession) -> ActualizarConfiguracionUseCase:
    return ActualizarConfiguracionUseCase(
        SqlAlchemyConfiguracionRepository(db), auditoria_usecase(db)
    )


def asignar_permisos_usecase(db: AsyncSession) -> AsignarPermisosUseCase:
    return AsignarPermisosUseCase(SqlAlchemyPermisoRepository(db), auditoria_usecase(db))
