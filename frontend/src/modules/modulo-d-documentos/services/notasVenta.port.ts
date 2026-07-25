// Puerto: interfaz de consulta/descarga de notas de venta.
import type { NotaVenta } from "../types";

export interface NotasVentaPort {
  listar(desde?: string, hasta?: string): Promise<NotaVenta[]>;
  descargarPng(ventaId: number): Promise<Blob>;
  descargarBatch(desde?: string, hasta?: string): Promise<Blob>;
  subirDriveBatch(desde?: string, hasta?: string, carpeta?: string): Promise<{ subidos: number; errores: number; total: number }>;
}
