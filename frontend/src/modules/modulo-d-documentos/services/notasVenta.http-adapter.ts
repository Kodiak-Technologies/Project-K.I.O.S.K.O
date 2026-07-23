// Adaptador: implementa notasVenta.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { NotasVentaPort } from "./notasVenta.port";

export const notasVentaHttpAdapter: NotasVentaPort = {
  async listar(desde, hasta) {
    const { data } = await httpClient.get("/notas-venta", { params: { desde, hasta } });
    return data;
  },

  async descargarPng(ventaId) {
    const { data } = await httpClient.get(`/notas-venta/${ventaId}/png`, {
      responseType: "blob",
    });
    return data;
  },

  async descargarBatch(desde, hasta) {
    const { data } = await httpClient.post(
      "/notas-venta/descargar",
      { desde, hasta },
      { responseType: "blob" }
    );
    return data;
  },

  async subirDriveBatch(desde, hasta, carpeta) {
    const { data } = await httpClient.post("/notas-venta/subir-drive", {
      desde,
      hasta,
      carpeta: carpeta ?? "Notas de Venta",
    });
    return data;
  },
};
