// Adaptador: implementa fiados.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { FiadosPort } from "./fiados.port";

export const fiadosHttpAdapter: FiadosPort = {
  async listar(buscar, incluirInactivos = false) {
    const { data } = await httpClient.get("/fiados/clientes", {
      params: { ...(buscar ? { buscar } : {}), ...(incluirInactivos ? { incluir_inactivos: true } : {}) },
    });
    return data;
  },
  async crear(datos) {
    const { data } = await httpClient.post("/fiados/clientes", datos);
    return data;
  },
  async estadoDeCuenta(clienteId) {
    const { data } = await httpClient.get(`/fiados/clientes/${clienteId}`);
    return data;
  },
  async actualizar(clienteId, cambios) {
    const { data } = await httpClient.patch(`/fiados/clientes/${clienteId}`, cambios);
    return data;
  },
  async pagar(clienteId, monto, metodo, nota) {
    const { data } = await httpClient.post(`/fiados/clientes/${clienteId}/pagos`, { monto, metodo, nota });
    return data;
  },
  async creditoPagado(clienteId, monto, metodo, nota) {
    const { data } = await httpClient.post(`/fiados/clientes/${clienteId}/creditos`, { monto, metodo, nota });
    return data;
  },
};
