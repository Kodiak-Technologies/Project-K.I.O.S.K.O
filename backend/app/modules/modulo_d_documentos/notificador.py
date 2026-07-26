# ⭐ CONTRATO PÚBLICO DE NOTIFICACIONES DEL MÓDULO D.
#
# Los módulos B y C avisan de eventos del negocio a través de este objeto (igual
# que usan `contenedor_a.auditoria_usecase(db)` para la bitácora). No conocen
# Telegram, correo ni la tabla `notificaciones`.
#
# Regla de oro: **una notificación caída NUNCA rompe la operación**. Si falla el
# envío o el guardado, se loguea y la venta / el ingreso / la apertura de caja
# siguen su curso. Por eso `avisar()` no propaga excepciones ni devuelve nada.
import logging

from app.modules.modulo_d_documentos.application.enviar_notificacion_usecase import (
    EnviarNotificacionUseCase,
)
from app.modules.modulo_d_documentos.domain.value_objects import TipoNotificacion

logger = logging.getLogger(__name__)


class Notificador:
    def __init__(self, enviar_usecase: EnviarNotificacionUseCase) -> None:
        self._enviar = enviar_usecase

    async def avisar(
        self,
        tipo: TipoNotificacion,
        titulo: str,
        mensaje: str,
        *,
        entidad_origen: str | None = None,
        entidad_id: str | int | None = None,
        usuario_id: int | None = None,
        producto_id: int | None = None,
    ) -> None:
        """Registra el aviso y lo envía por los canales configurados.

        `usuario_id=None` = aviso para la administradora: además de quedar en la
        bandeja, sale por Telegram y correo. Con un `usuario_id` concreto, solo
        queda en la bandeja de esa persona.
        """
        try:
            await self._enviar.ejecutar(
                tipo=tipo.value if isinstance(tipo, TipoNotificacion) else str(tipo),
                titulo=titulo,
                mensaje=mensaje,
                entidad_origen=entidad_origen,
                entidad_id=str(entidad_id) if entidad_id is not None else None,
                usuario_id=usuario_id,
                producto_id=producto_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "No se pudo notificar (%s) '%s': %s", tipo, titulo, exc, exc_info=True
            )
