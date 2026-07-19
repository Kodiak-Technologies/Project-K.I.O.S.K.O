// Adaptador: implementa caja.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { CajaPort } from "./caja.port";

export const cajaHttpAdapter: CajaPort = {
  async turnoActual() {
    const { data } = await httpClient.get("/caja/turno-actual");
    return data;
  },
  async abrir(monto_inicial) {
    const { data } = await httpClient.post("/caja/abrir", { monto_inicial });
    return data;
  },
  async resumen() {
    const { data } = await httpClient.get("/caja/resumen");
    return data;
  },
  async cerrar(monto_final, comentario) {
    const { data } = await httpClient.post("/caja/cerrar", { monto_final, comentario });
    return data;
  },
  async turnos(limite = 30) {
    const { data } = await httpClient.get("/caja/turnos", { params: { limite } });
    return data;
  },
  async editar(turnoId, datos) {
    const { data } = await httpClient.patch(`/caja/turnos/${turnoId}`, datos);
    return data;
  },
  async movimientos(turnoId) {
    const { data } = await httpClient.get(`/caja/turnos/${turnoId}/movimientos`);
    return data;
  },
};
