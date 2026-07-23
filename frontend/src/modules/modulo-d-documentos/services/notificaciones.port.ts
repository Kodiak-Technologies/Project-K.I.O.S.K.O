// Puerto: interfaz de consulta/envío de notificaciones.
import type { ConfigNotificaciones, Notificacion } from "../types";

export interface NotificacionesPort {
  listar(): Promise<Notificacion[]>;
  marcarLeida(id: number): Promise<void>;
  marcarTodasLeidas(): Promise<void>;
  obtenerConfig(): Promise<ConfigNotificaciones>;
  actualizarConfig(config: Partial<ConfigNotificaciones>): Promise<ConfigNotificaciones>;
}
