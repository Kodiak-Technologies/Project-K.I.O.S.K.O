# Caso de uso: consultar el estado de la caja (turno actual e historial de turnos).
# El historial es visible para TODOS los usuarios autenticados: en un cambio de
# turno, el cajero entrante ve con cuánto abrió y cerró el anterior; el admin
# supervisa lo mismo de todos sus cajeros.
from app.modules.modulo_c_ventas.domain.entities import TurnoCaja
from app.modules.modulo_c_ventas.domain.ports.caja_repository_port import CajaRepositoryPort


class ConsultarCajaUseCase:
    def __init__(self, caja_repo: CajaRepositoryPort):
        self._caja = caja_repo

    async def turno_actual(self) -> TurnoCaja | None:
        return await self._caja.turno_abierto()

    async def historial(self, limite: int = 30) -> list[TurnoCaja]:
        return await self._caja.listar(limite)
