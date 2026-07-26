# Caso de uso: registrar una compra a crédito a un proveedor (HU-B14, REQ-CC).
# - SELECT proveedor FOR UPDATE.
# - INSERT pagos_proveedor con tipo='compra_credito'.
# - UPDATE proveedor SET deuda_actual = deuda_actual + :monto (atómico).
# - Si se pasa solicitud_ingreso_id, valida que la solicitud existe.
from datetime import datetime, date as date_type
from decimal import Decimal

from app.modules.modulo_a_seguridad.application.registrar_auditoria_usecase import (
    RegistrarAuditoriaUseCase,
)
from app.modules.modulo_b_inventario.domain.entities import PagoProveedor
from app.modules.modulo_b_inventario.domain.ports.pago_proveedor_repository_port import (
    PagoProveedorRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.proveedor_repository_port import (
    ProveedorRepositoryPort,
)
from app.modules.modulo_b_inventario.domain.ports.solicitud_ingreso_repository_port import (
    SolicitudIngresoRepositoryPort,
)
from app.shared.kernel.exceptions import (
    NoEncontradoError,
    ValidacionError,
)


class RegistrarCompraCreditoUseCase:
    def __init__(
        self,
        proveedor_repo: ProveedorRepositoryPort,
        pago_repo: PagoProveedorRepositoryPort,
        solicitud_repo: SolicitudIngresoRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._proveedores = proveedor_repo
        self._pagos = pago_repo
        self._solicitudes = solicitud_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        proveedor_id: int,
        monto: Decimal,
        fecha: date_type | str | datetime,
        concepto: str | None,
        solicitud_ingreso_id: int | None,
        usuario_id: int,
        usuario_nombre: str,
        ip: str = "",
        user_agent: str = "",
    ) -> PagoProveedor:
        if monto is None or Decimal(str(monto)) <= 0:
            raise ValidacionError("El monto debe ser mayor a 0.")
        # FOR UPDATE
        prov = await self._proveedores.find_by_id_for_update(proveedor_id)
        if prov is None:
            raise NoEncontradoError("El proveedor no existe.")
        # No se le puede seguir comprando a un proveedor dado de baja (los
        # pagos SÍ se permiten, para poder saldar la deuda existente).
        if not prov.activo:
            raise ValidacionError(
                "El proveedor está inactivo: no se pueden registrar compras a crédito."
            )
        if solicitud_ingreso_id is not None:
            sol = await self._solicitudes.find_by_id(solicitud_ingreso_id)
            if sol is None:
                raise NoEncontradoError("La solicitud de ingreso no existe.")
        # Normalizar fecha
        if isinstance(fecha, str):
            try:
                fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                raise ValidacionError(
                    "Fecha inválida. Formato esperado: YYYY-MM-DD."
                )
        elif isinstance(fecha, datetime):
            fecha_dt = fecha.date()
        else:
            fecha_dt = fecha
        # INSERT pago_proveedor
        pago = PagoProveedor.crear_compra_credito(
            proveedor_id=proveedor_id,
            monto=Decimal(str(monto)),
            fecha=datetime.combine(fecha_dt, datetime.min.time()),
            concepto=concepto,
            usuario_id=usuario_id,
            usuario_nombre=usuario_nombre,
            solicitud_ingreso_id=solicitud_ingreso_id,
        )
        await self._pagos.crear(pago)
        # UPDATE deuda atómico
        ok = await self._proveedores.incrementar_deuda_atomic(
            proveedor_id, Decimal(str(monto))
        )
        if not ok:
            # No debería fallar (la deuda solo crece), pero defensivo.
            raise ValidacionError("No se pudo actualizar la deuda del proveedor.")
        await self._auditoria.ejecutar(
            accion="compra_credito",
            entidad="proveedores",
            usuario_id=usuario_id,
            rol="",
            entidad_id=proveedor_id,
            valor_nuevo={
                "monto": float(monto),
                "solicitud_ingreso_id": solicitud_ingreso_id,
                "concepto": concepto,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return pago
