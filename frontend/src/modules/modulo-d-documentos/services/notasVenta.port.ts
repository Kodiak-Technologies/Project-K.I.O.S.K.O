// Puerto: interfaz de consulta/descarga de notas de venta.
import type { FiltrosNotasVenta, NotasVentaPaginadas } from "../types";

export interface NotasVentaPort {
  listar(filtros?: FiltrosNotasVenta): Promise<NotasVentaPaginadas>;
  descargarPng(ventaId: number): Promise<Blob>;
  descargarBatch(desde?: string, hasta?: string): Promise<Blob>;
}
