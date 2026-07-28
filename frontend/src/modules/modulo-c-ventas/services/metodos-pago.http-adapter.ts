// Adaptador: implementa metodos-pago.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { MetodosPagoPort } from "./metodos-pago.port";

export const metodosPagoHttpAdapter: MetodosPagoPort = {
  async listar(todos = false) {
    const { data } = await httpClient.get("/metodos-pago", { params: todos ? { todos } : undefined });
    return data;
  },
  async crear(datos) {
    const { data } = await httpClient.post("/metodos-pago", datos);
    return data;
  },
  async actualizar(id, cambios) {
    const { data } = await httpClient.patch(`/metodos-pago/${id}`, cambios);
    return data;
  },
};
