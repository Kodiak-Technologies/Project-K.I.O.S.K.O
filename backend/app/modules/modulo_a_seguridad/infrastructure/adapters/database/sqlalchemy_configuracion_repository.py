# Adaptador: implementa ConfiguracionRepositoryPort (fila única id=1) usando SQLAlchemy async.
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulo_a_seguridad.domain.entities import ConfiguracionNegocio
from app.modules.modulo_a_seguridad.infrastructure.adapters.database.models import (
    ConfiguracionNegocioModel,
)
from app.shared.kernel.exceptions import NoEncontradoError


def _a_entidad(fila: ConfiguracionNegocioModel) -> ConfiguracionNegocio:
    return ConfiguracionNegocio(
        id=fila.id,
        nombre_negocio=fila.nombre_negocio,
        logo_url=fila.logo_url,
        color_primario=fila.color_primario,
        color_secundario=fila.color_secundario,
        tipografia=fila.tipografia,
        session_ttl_admin_minutos=fila.session_ttl_admin_minutos,
        session_ttl_cajero_minutos=fila.session_ttl_cajero_minutos,
        max_intentos_login=fila.max_intentos_login,
        minutos_bloqueo=fila.minutos_bloqueo,
        margen_ganancia_default=fila.margen_ganancia_default,
        updated_by=fila.updated_by,
        updated_at=fila.updated_at,
    )


class SqlAlchemyConfiguracionRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def obtener(self) -> ConfiguracionNegocio:
        fila = await self._db.get(ConfiguracionNegocioModel, 1)
        if fila is None:
            raise NoEncontradoError("La configuración del negocio no está inicializada (corre el seed).")
        return _a_entidad(fila)

    async def actualizar(self, configuracion: ConfiguracionNegocio) -> ConfiguracionNegocio:
        fila = await self._db.get(ConfiguracionNegocioModel, 1)
        if fila is None:
            raise NoEncontradoError("La configuración del negocio no está inicializada (corre el seed).")
        fila.nombre_negocio = configuracion.nombre_negocio
        fila.logo_url = configuracion.logo_url
        fila.color_primario = configuracion.color_primario
        fila.color_secundario = configuracion.color_secundario
        fila.tipografia = configuracion.tipografia
        fila.session_ttl_admin_minutos = configuracion.session_ttl_admin_minutos
        fila.session_ttl_cajero_minutos = configuracion.session_ttl_cajero_minutos
        fila.max_intentos_login = configuracion.max_intentos_login
        fila.minutos_bloqueo = configuracion.minutos_bloqueo
        fila.margen_ganancia_default = configuracion.margen_ganancia_default
        fila.updated_by = configuracion.updated_by
        await self._db.flush()
        # updated_at lo genera la BD en el UPDATE (onupdate=func.now()), así que tras
        # el flush queda "expirado". Hay que recargarlo con refresh() async: leerlo
        # directo dispararía una carga síncrona y explota con MissingGreenlet.
        await self._db.refresh(fila)
        return _a_entidad(fila)
