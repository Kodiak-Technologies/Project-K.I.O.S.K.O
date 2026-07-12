# Router HTTP: /configuracion. Lectura para cualquier autenticado (los módulos B/C/D
# la consumen: logo y nombre van en boletas y correos); escritura solo ADMIN.
import base64

from fastapi import APIRouter, Depends, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad import module_container as contenedor
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.sqlalchemy_configuracion_repository import (
    SqlAlchemyConfiguracionRepository,
)
from app.modules.modulo_a_seguridad.infrastructure.dependencies import (
    contexto_request,
    get_current_user,
    require_permission,
)
from app.modules.modulo_a_seguridad.infrastructure.http.schemas import (
    ActualizarConfiguracionRequest,
    ConfiguracionResponse,
)
from app.shared.database.session import get_db
from app.shared.kernel.exceptions import ValidacionError

router = APIRouter(prefix="/configuracion", tags=["Configuración"])

_solo_editar_config = require_permission("configuracion.editar")

_TIPOS_LOGO = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
_TAMANO_MAX_LOGO = 500 * 1024  # 500 KB: el logo se guarda como data-URI en BD


@router.get("", response_model=ConfiguracionResponse)
async def obtener(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await SqlAlchemyConfiguracionRepository(db).obtener()
    return ConfiguracionResponse.desde_entidad(config)


@router.patch("", response_model=ConfiguracionResponse)
async def actualizar(
    datos: ActualizarConfiguracionRequest,
    request: Request,
    admin: Usuario = Depends(_solo_editar_config),
    db: AsyncSession = Depends(get_db),
):
    ip, user_agent = contexto_request(request)
    actualizada = await contenedor.actualizar_configuracion_usecase(db).ejecutar(
        admin, datos.model_dump(exclude_unset=True), ip, user_agent
    )
    return ConfiguracionResponse.desde_entidad(actualizada)


@router.post("/logo", response_model=ConfiguracionResponse)
async def subir_logo(
    archivo: UploadFile,
    request: Request,
    admin: Usuario = Depends(_solo_editar_config),
    db: AsyncSession = Depends(get_db),
):
    if archivo.content_type not in _TIPOS_LOGO:
        raise ValidacionError("Formato de logo no soportado (usa PNG, JPEG, WebP o SVG).")
    contenido = await archivo.read()
    if len(contenido) > _TAMANO_MAX_LOGO:
        raise ValidacionError("El logo no puede superar los 500 KB.")

    data_uri = f"data:{archivo.content_type};base64,{base64.b64encode(contenido).decode()}"
    ip, user_agent = contexto_request(request)
    actualizada = await contenedor.actualizar_configuracion_usecase(db).ejecutar(
        admin, {"logo_url": data_uri}, ip, user_agent
    )
    return ConfiguracionResponse.desde_entidad(actualizada)
