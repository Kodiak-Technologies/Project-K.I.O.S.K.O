// Adaptador: implementa notificaciones.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { NotificacionesPort } from "./notificaciones.port";

export const notificacionesHttpAdapter: NotificacionesPort = {
  async listar() {
    const { data } = await httpClient.get("/notificaciones");
    return data;
  },
  async marcarLeida(id) {
    await httpClient.post(`/notificaciones/${id}/leida`);
  },
};
