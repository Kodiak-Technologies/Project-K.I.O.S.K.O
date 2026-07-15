from typing import Protocol


class ReporteGeneratorPort(Protocol):
    async def generar_excel(self, datos: dict, nombre: str) -> bytes:
        """Genera un archivo Excel con los datos proporcionados. Retorna los bytes del archivo."""
        ...
