// Adaptador: implementa notificaciones.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { NotificacionesPort } from "./notificaciones.port";

export const notificacionesHttpAdapter: NotificacionesPort = {
  async listar(page = 1, pageSize = 20) {
    const { data } = await httpClient.get("/notificaciones", {
      params: { page, page_size: pageSize },
    });
    return data;
  },
  async marcarLeida(id) {
    await httpClient.post(`/notificaciones/${id}/leida`);
  },
  async marcarTodasLeidas() {
    await httpClient.post("/notificaciones/leer-todas");
  },
  async obtenerConfig() {
    const { data } = await httpClient.get("/notificaciones/config");
    return data;
  },
  async actualizarConfig(config) {
    const { data } = await httpClient.put("/notificaciones/config", config);
    return data;
  },
};
