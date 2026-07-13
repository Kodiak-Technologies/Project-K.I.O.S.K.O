// Puerto: interfaz de consulta/envío de notificaciones.
import type { Notificacion } from "../types";

export interface NotificacionesPort {
  listar(): Promise<Notificacion[]>;
  marcarLeida(id: number): Promise<void>;
}
