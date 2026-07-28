// Puerto: interfaz de consulta/envío de notificaciones.
import type {
  ConfigNotificaciones,
  Notificacion,
  NotificacionesPaginadas,
} from "../types";

export interface NotificacionesPort {
  listar(page?: number, pageSize?: number): Promise<NotificacionesPaginadas>;
  marcarLeida(id: number): Promise<void>;
  marcarTodasLeidas(): Promise<void>;
  obtenerConfig(): Promise<ConfigNotificaciones>;
  actualizarConfig(config: Partial<ConfigNotificaciones>): Promise<ConfigNotificaciones>;
}
