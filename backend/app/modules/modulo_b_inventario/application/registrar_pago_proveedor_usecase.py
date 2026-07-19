# Caso de uso: registrar un pago a un proveedor (HU-B14, REQ-PAG).
# - SELECT proveedor FOR UPDATE.
# - Valida monto > 0 y monto <= deuda_actual.
# - INSERT pagos_proveedor con tipo='pago'.
# - UPDATE deuda_actual = deuda_actual - :monto.
from datetime import date as date_type, datetime
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
from app.shared.kernel.exceptions import (
    NoEncontradoError,
    ValidacionError,
)


class RegistrarPagoProveedorUseCase:
    def __init__(
        self,
        proveedor_repo: ProveedorRepositoryPort,
        pago_repo: PagoProveedorRepositoryPort,
        auditoria: RegistrarAuditoriaUseCase,
    ):
        self._proveedores = proveedor_repo
        self._pagos = pago_repo
        self._auditoria = auditoria

    async def ejecutar(
        self,
        proveedor_id: int,
        monto: Decimal,
        fecha: date_type | str | datetime,
        concepto: str | None,
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
        monto_dec = Decimal(str(monto))
        if monto_dec > prov.deuda_actual:
            raise ValidacionError("El pago no puede superar la deuda actual.")
        if isinstance(fecha, str):
            try:
                fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                raise ValidacionError("Fecha inválida. Formato esperado: YYYY-MM-DD.")
        elif isinstance(fecha, datetime):
            fecha_dt = fecha.date()
        else:
            fecha_dt = fecha
        pago = PagoProveedor.crear_pago(
            proveedor_id=proveedor_id,
            monto=monto_dec,
            fecha=datetime.combine(fecha_dt, datetime.min.time()),
            concepto=concepto,
            usuario_id=usuario_id,
            usuario_nombre=usuario_nombre,
        )
        await self._pagos.crear(pago)
        ok = await self._proveedores.incrementar_deuda_atomic(
            proveedor_id, -monto_dec
        )
        if not ok:
            raise ValidacionError("No se pudo actualizar la deuda del proveedor.")
        await self._auditoria.ejecutar(
            accion="pago_proveedor",
            entidad="proveedores",
            usuario_id=usuario_id,
            rol="",
            entidad_id=proveedor_id,
            valor_nuevo={
                "monto": float(monto),
                "concepto": concepto,
            },
            ip=ip,
            user_agent=user_agent,
        )
        return pago
