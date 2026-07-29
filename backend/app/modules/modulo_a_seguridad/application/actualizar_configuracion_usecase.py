# Caso de uso: actualizar la configuración e identidad visual (solo ADMIN).
# Cualquier usuario autenticado puede LEERLA (GET /configuracion); eso no pasa por aquí.
from dataclasses import asdict
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_a_seguridad.domain.entities import ConfiguracionNegocio, Usuario
from app.modules.modulo_a_seguridad.domain.ports.configuracion_repository_port import (
    ConfiguracionRepositoryPort,
)
from app.shared.kernel.exceptions import ValidacionError

# Campos que el PATCH puede tocar (todo lo demás se ignora).
_CAMPOS_EDITABLES = {
    "nombre_negocio", "logo_url", "color_primario", "color_secundario", "tipografia",
    "session_ttl_admin_minutos", "session_ttl_cajero_minutos",
    "max_intentos_login", "minutos_bloqueo", "margen_ganancia_default",
}
_CAMPOS_ENTEROS_POSITIVOS = {
    "session_ttl_admin_minutos", "session_ttl_cajero_minutos",
    "max_intentos_login", "minutos_bloqueo",
}


class ActualizarConfiguracionUseCase:
    def __init__(
        self,
        configuracion_repo: ConfiguracionRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._configuracion = configuracion_repo
        self._auditoria = auditoria

    async def ejecutar(
        self, admin: Usuario, cambios: dict, ip: str, user_agent: str
    ) -> ConfiguracionNegocio:
        config = await self._configuracion.obtener()
        anterior = asdict(config)

        for campo, valor in cambios.items():
            if campo not in _CAMPOS_EDITABLES or valor is None:
                continue
            if campo in _CAMPOS_ENTEROS_POSITIVOS and (not isinstance(valor, int) or valor <= 0):
                raise ValidacionError(f"'{campo}' debe ser un entero positivo.")
            if campo == "margen_ganancia_default":
                # La columna es NUMERIC: pasar el float directo arrastraría el
                # error binario al precio de venta que se calcula con él.
                valor = Decimal(str(valor))
                if valor < 0:
                    raise ValidacionError("El margen de ganancia no puede ser negativo.")
            setattr(config, campo, valor)

        config.updated_by = admin.id
        actualizada = await self._configuracion.actualizar(config)

        await self._auditoria.ejecutar(
            accion="configuracion_actualizada", entidad="configuracion_negocio",
            usuario_id=admin.id, rol=admin.rol_nombre, entidad_id=1,
            valor_anterior={k: anterior[k] for k in _CAMPOS_EDITABLES},
            valor_nuevo={k: getattr(actualizada, k) for k in _CAMPOS_EDITABLES},
            ip=ip, user_agent=user_agent,
        )
        return actualizada
