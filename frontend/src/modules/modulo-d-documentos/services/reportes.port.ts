// Puerto: interfaz de generación/consulta de reportes de ventas.
import type { ResumenReporte } from "../types";

export interface ReportesPort {
  resumen(desde: string, hasta: string): Promise<ResumenReporte>;
}
