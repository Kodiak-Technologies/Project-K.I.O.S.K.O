// Adaptador: implementa notasVenta.port.ts usando el cliente HTTP compartido (axios).
import { httpClient, TIMEOUT_ARCHIVOS_MS } from "../../../shared/lib/http-client";
import type { NotasVentaPort } from "./notasVenta.port";

export const notasVentaHttpAdapter: NotasVentaPort = {
  async listar(filtros) {
    const params: Record<string, unknown> = {};
    for (const [clave, valor] of Object.entries(filtros ?? {})) {
      if (valor !== undefined && valor !== null && valor !== "") params[clave] = valor;
    }
    const { data } = await httpClient.get("/notas-venta", { params });
    return data;
  },

  async descargarPng(ventaId) {
    const { data } = await httpClient.get(`/notas-venta/${ventaId}/png`, {
      responseType: "blob",
      timeout: TIMEOUT_ARCHIVOS_MS,
    });
    return data;
  },

  async subirADrive(ventaId) {
    const { data } = await httpClient.post(`/notas-venta/${ventaId}/drive`, undefined, {
      timeout: TIMEOUT_ARCHIVOS_MS,
    });
    return data;
  },

  async descargarBatch(desde, hasta) {
    const { data } = await httpClient.post(
      "/notas-venta/descargar",
      { desde, hasta },
      { responseType: "blob", timeout: TIMEOUT_ARCHIVOS_MS }
    );
    return data;
  },
};
