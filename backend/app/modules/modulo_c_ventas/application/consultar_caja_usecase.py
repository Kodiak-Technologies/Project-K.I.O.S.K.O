# Caso de uso: consultar el estado de la caja (turno actual, resumen e historial).
# El historial es visible para TODOS los usuarios autenticados: en un cambio de
# turno, el cajero entrante ve con cuánto abrió y cerró el anterior; el admin
# supervisa lo mismo de todos sus cajeros.
from app.modules.modulo_c_ventas.application.cerrar_caja_usecase import calcular_resumen
from app.modules.modulo_c_ventas.domain.entities import (
    Anulacion,
    ArqueoCaja,
    ResumenCaja,
    TurnoCaja,
    Venta,
)
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort
from app.modules.modulo_c_ventas.domain.ports.venta_repository_port import VentaRepositoryPort
from app.shared.kernel.exceptions import ConflictoError, NoEncontradoError


class ConsultarCajaUseCase:
    def __init__(
        self,
        caja_repo: CajaRepositoryPort,
        venta_repo: VentaRepositoryPort,
    ):
        self._caja = caja_repo
        self._ventas = venta_repo

    async def turno_actual(self) -> TurnoCaja | None:
        return await self._caja.turno_abierto()

    async def resumen(self) -> ResumenCaja:
        """La sugerencia de cierre del turno abierto (RF-17)."""
        turno = await self._caja.turno_abierto()
        if turno is None:
            raise ConflictoError("No hay un turno de caja abierto.")
        return await calcular_resumen(self._caja, turno)

    async def historial(self, limite: int = 30) -> list[tuple[TurnoCaja, ArqueoCaja | None]]:
        turnos = await self._caja.listar(limite)
        arqueos = await self._caja.arqueos_por_turno([t.id for t in turnos])
        return [(t, arqueos.get(t.id)) for t in turnos]

    async def movimientos(self, turno_id: int) -> tuple[list[Venta], list[Anulacion]]:
        """El RASTRO de un turno para el panel de la administradora (HU-C08):
        ventas del turno y reversos hechos durante él."""
        if await self._caja.buscar_por_id(turno_id) is None:
            raise NoEncontradoError("Turno no encontrado.")
        ventas = await self._ventas.listar(turno_id=turno_id)
        reversos = await self._ventas.anulaciones_de_turno(turno_id)
        return ventas, reversos
