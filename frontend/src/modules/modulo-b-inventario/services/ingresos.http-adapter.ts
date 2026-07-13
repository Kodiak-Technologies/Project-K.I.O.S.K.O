// Adaptador: implementa ingresos.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { IngresosPort } from "./ingresos.port";

export const ingresosHttpAdapter: IngresosPort = {
  async listar() {
    const { data } = await httpClient.get("/ingresos");
    return data;
  },
  async solicitar(producto_id, cantidad) {
    const { data } = await httpClient.post("/ingresos", { producto_id, cantidad });
    return data;
  },
  async aprobar(id) {
    const { data } = await httpClient.post(`/ingresos/${id}/aprobar`);
    return data;
  },
  async rechazar(id, motivo) {
    const { data } = await httpClient.post(`/ingresos/${id}/rechazar`, { motivo });
    return data;
  },
};
