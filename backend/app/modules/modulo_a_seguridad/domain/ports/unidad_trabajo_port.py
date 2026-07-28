# Puerto: confirma la transacción en curso. Lo necesita el login para que los
# intentos fallidos y su registro en bitácora SOBREVIVAN al rollback que produce
# lanzar la excepción 401 (si no, un atacante tendría intentos infinitos).
from typing import Protocol


class UnidadTrabajoPort(Protocol):
    async def confirmar(self) -> None: ...
