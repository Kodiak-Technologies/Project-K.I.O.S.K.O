// Adaptador: implementa reportes.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { ReportesPort } from "./reportes.port";

export const reportesHttpAdapter: ReportesPort = {
  async resumen(desde, hasta) {
    const { data } = await httpClient.get("/reportes/resumen", { params: { desde, hasta } });
    return data;
  },
  async masVendidos(desde, hasta, criterio = "unidades", orden = "mayor") {
    const { data } = await httpClient.get("/reportes/mas-vendidos", {
      params: { desde, hasta, criterio, orden },
    });
    return data;
  },
};
