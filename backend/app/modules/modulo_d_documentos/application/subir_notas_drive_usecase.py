import logging

from app.modules.modulo_d_documentos.application.generar_nota_venta_usecase import GenerarNotaVentaUseCase
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort
from app.modules.modulo_d_documentos.domain.ports.drive_storage_port import DriveStoragePort

logger = logging.getLogger(__name__)


class SubirNotasDriveUseCase:
    def __init__(
        self,
        venta_data: VentaDataProviderPort,
        generar_nota: GenerarNotaVentaUseCase,
        drive_storage: DriveStoragePort,
    ) -> None:
        self._venta_data = venta_data
        self._generar_nota = generar_nota
        self._drive_storage = drive_storage

    async def ejecutar(
        self,
        desde: str | None = None,
        hasta: str | None = None,
        carpeta: str = "Notas de Venta",
    ) -> dict:
        ventas = await self._venta_data.listar_ventas(desde=desde, hasta=hasta)

        subidos = 0
        errores = 0

        for venta in ventas:
            venta_id = venta["id"]
            try:
                png_bytes = await self._generar_nota.ejecutar(venta_id)
                fecha = venta.get("fecha", "")
                if hasattr(fecha, "strftime"):
                    fecha_str = fecha.strftime("%Y-%m-%d")
                    anio = fecha.strftime("%Y")
                    mes = fecha.strftime("%m")
                else:
                    fecha_str = str(fecha)[:10]
                    anio = fecha_str[:4]
                    mes = fecha_str[5:7]
                nombre = f"{fecha_str}_VENTA-{venta_id}.png"
                carpeta_con_fecha = f"{carpeta}/{anio}/{mes}"
                await self._drive_storage.subir(
                    archivo_bytes=png_bytes,
                    nombre=nombre,
                    carpeta=carpeta_con_fecha,
                )
                subidos += 1
            except Exception as e:
                errores += 1
                logger.error("Error subiendo venta %d a Drive: %s", venta_id, e)

        return {"subidos": subidos, "errores": errores, "total": len(ventas)}
