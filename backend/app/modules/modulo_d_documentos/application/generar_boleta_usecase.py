from app.modules.modulo_d_documentos.domain.entities import Boleta
from app.modules.modulo_d_documentos.domain.ports.boleta_repository_port import BoletaRepositoryPort
from app.modules.modulo_d_documentos.domain.ports.venta_data_provider_port import VentaDataProviderPort
from app.modules.modulo_d_documentos.domain.ports.configuracion_provider_port import ConfiguracionProviderPort
from app.shared.kernel.exceptions import NoEncontradoError, ValidacionError


class GenerarBoletaUseCase:
    def __init__(
        self,
        boleta_repo: BoletaRepositoryPort,
        venta_data: VentaDataProviderPort,
        config_data: ConfiguracionProviderPort,
    ) -> None:
        self._boleta_repo = boleta_repo
        self._venta_data = venta_data
        self._config_data = config_data

    async def ejecutar(self, venta_id: int) -> Boleta:
        venta = await self._venta_data.obtener_venta(venta_id)
        if venta is None:
            raise NoEncontradoError(f"La venta #{venta_id} no existe.")

        existente = await self._boleta_repo.buscar_por_venta_id(venta_id)
        if existente is not None:
            raise ValidacionError(f"La venta #{venta_id} ya tiene boleta: {existente.numero}.")

        numero = await self._boleta_repo.generar_siguiente_numero()

        boleta = Boleta(
            id=None,
            venta_id=venta_id,
            numero=numero,
            total=venta.get("total", 0.0),
        )

        return await self._boleta_repo.crear(boleta)
