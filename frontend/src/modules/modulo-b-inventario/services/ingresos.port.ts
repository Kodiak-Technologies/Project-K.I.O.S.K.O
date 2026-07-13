// Puerto: interfaz de registro/aprobación/rechazo de ingresos de mercadería.
import type { IngresoMercaderia } from "../types";

export interface IngresosPort {
  listar(): Promise<IngresoMercaderia[]>;
  solicitar(producto_id: number, cantidad: number): Promise<IngresoMercaderia>;
  aprobar(id: number): Promise<IngresoMercaderia>;
  rechazar(id: number, motivo: string): Promise<IngresoMercaderia>;
}
