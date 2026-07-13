// Adaptador: implementa ventas.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { VentasPort } from "./ventas.port";

export const ventasHttpAdapter: VentasPort = {
  async registrar(venta) {
    const { data } = await httpClient.post("/ventas", venta);
    return data;
  },
  async anular(id, motivo) {
    const { data } = await httpClient.post(`/ventas/${id}/anular`, { motivo });
    return data;
  },
  async listar(desde, hasta) {
    const { data } = await httpClient.get("/ventas", { params: { desde, hasta } });
    return data;
  },
};
