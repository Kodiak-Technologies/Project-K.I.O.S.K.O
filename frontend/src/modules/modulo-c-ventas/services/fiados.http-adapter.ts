// Adaptador: implementa fiados.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { FiadosPort } from "./fiados.port";

export const fiadosHttpAdapter: FiadosPort = {
  async listarClientes(q) {
    const { data } = await httpClient.get("/clientes", { params: q ? { q } : undefined });
    return data;
  },
  async crearCliente(datos) {
    const { data } = await httpClient.post("/clientes", datos);
    return data;
  },
  async actualizarCliente(id, cambios) {
    const { data } = await httpClient.patch(`/clientes/${id}`, cambios);
    return data;
  },
  async fijarLimiteCredito(id, limite) {
    const { data } = await httpClient.patch(`/clientes/${id}/limite-credito`, {
      limite_credito: limite,
    });
    return data;
  },
  async listarFiados(clienteId, pendientes = true) {
    const { data } = await httpClient.get("/fiados", {
      params: { cliente_id: clienteId, pendientes },
    });
    return data;
  },
  async abonosDeFiado(fiadoId) {
    const { data } = await httpClient.get(`/fiados/${fiadoId}/abonos`);
    return data;
  },
  async registrarAbono(fiadoId, monto, metodo) {
    const { data } = await httpClient.post(`/fiados/${fiadoId}/abonos`, { monto, metodo });
    return data;
  },
};
