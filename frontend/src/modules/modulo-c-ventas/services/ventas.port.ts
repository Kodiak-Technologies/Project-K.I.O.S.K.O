// Puerto: interfaz de registro/anulación/devolución/consulta de ventas.
import type { NuevaVenta, Venta } from "../types";

export interface VentasPort {
  registrar(venta: NuevaVenta): Promise<Venta>;
  anular(id: number, motivo: string): Promise<Venta>;
  /** Devolución parcial: líneas (detalle_id) y cantidades a reponer. */
  devolver(id: number, items: { detalle_id: number; cantidad: number }[], motivo: string): Promise<Venta>;
  listar(desde?: string, hasta?: string): Promise<Venta[]>;
}
