// Puerto: interfaz de registro/anulación/consulta de ventas.
import type { NuevaVenta, Venta } from "../types";

export interface VentasPort {
  registrar(venta: NuevaVenta): Promise<Venta>;
  anular(id: number, motivo: string): Promise<Venta>;
  listar(desde?: string, hasta?: string): Promise<Venta[]>;
}
