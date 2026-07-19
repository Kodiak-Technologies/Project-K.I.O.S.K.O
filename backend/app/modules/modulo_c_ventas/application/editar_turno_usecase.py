from decimal import Decimal
from app.modules.modulo_a_seguridad.domain.entities import Usuario
from app.modules.modulo_c_ventas.domain.entities import TurnoCaja
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.shared.kernel.exceptions import NoEncontradoError, ProhibidoError, ValidacionError


class EditarTurnoUseCase:
    def __init__(self, caja_repo: CajaRepositoryPort):
        self._caja = caja_repo

    async def ejecutar(
        self,
        admin: Usuario,
        turno_id: int,
        actualizaciones: dict,
    ) -> TurnoCaja:
        if admin.rol_nombre != "ADMIN":
            raise ProhibidoError("Solo un administrador puede editar turnos de caja.")

        turno = await self._caja.buscar_por_id(turno_id)
        if not turno:
            raise NoEncontradoError(f"Turno de caja {turno_id} no encontrado.")

        if "asignado_a_id" in actualizaciones:
            turno.asignado_a_id = actualizaciones["asignado_a_id"]
            
        if "monto_inicial" in actualizaciones:
            monto = actualizaciones["monto_inicial"]
            if monto is not None:
                if monto < 0:
                    raise ValidacionError("El monto inicial no puede ser negativo.")
                turno.monto_inicial = Decimal(str(monto))

        return await self._caja.actualizar(turno)
