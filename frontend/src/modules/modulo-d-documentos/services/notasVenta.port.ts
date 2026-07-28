// Puerto: interfaz de consulta/descarga de notas de venta.
import type {
  FiltrosNotasVenta,
  NotasVentaPaginadas,
  SubirNotaDriveRespuesta,
} from "../types";

export interface NotasVentaPort {
  listar(filtros?: FiltrosNotasVenta): Promise<NotasVentaPaginadas>;
  descargarPng(ventaId: number): Promise<Blob>;
  descargarBatch(desde?: string, hasta?: string): Promise<Blob>;
  /** Archiva la nota en `boletas/ventas` del Drive del negocio. */
  subirADrive(ventaId: number): Promise<SubirNotaDriveRespuesta>;
}
