import io
import zipfile

from app.modules.modulo_d_documentos.application.generar_nota_venta_usecase import GenerarNotaVentaUseCase
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort


class DescargarNotasVentaUseCase:
    def __init__(
        self,
        venta_data: VentaDataProviderPort,
        generar_nota: GenerarNotaVentaUseCase,
    ) -> None:
        self._venta_data = venta_data
        self._generar_nota = generar_nota

    async def ejecutar(self, desde: str | None = None, hasta: str | None = None) -> tuple[bytes, int]:
        ventas = await self._venta_data.listar_ventas(desde=desde, hasta=hasta)

        if not ventas:
            return b"", 0

        if len(ventas) == 1:
            png_bytes = await self._generar_nota.ejecutar(ventas[0]["id"])
            return png_bytes, 1

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for venta in ventas:
                venta_id = venta["id"]
                try:
                    png_bytes = await self._generar_nota.ejecutar(venta_id)
                    fecha = venta.get("fecha", "")
                    if hasattr(fecha, "strftime"):
                        fecha = fecha.strftime("%Y-%m-%d")
                    nombre = f"{str(fecha)[:10]}_VENTA-{venta_id}.png"
                    zf.writestr(nombre, png_bytes)
                except Exception:
                    continue

        return buffer.getvalue(), len(ventas)
