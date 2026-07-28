// Puerto: interfaz de generación/consulta de reportes de ventas.
import type { ResumenReporte, TopProducto } from "../types";

export interface ReportesPort {
  resumen(desde: string, hasta: string): Promise<ResumenReporte>;
  masVendidos(desde: string, hasta: string, criterio?: string, orden?: string): Promise<TopProducto[]>;
  exportar(desde: string, hasta: string, tipo?: string): Promise<Blob>;
}
