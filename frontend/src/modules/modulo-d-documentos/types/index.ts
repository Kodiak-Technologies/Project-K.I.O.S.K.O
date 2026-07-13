// Tipos/DTOs del módulo de documentos (contrato esperado del backend de Fabrizio).

export interface Boleta {
  id: number;
  venta_id: number;
  numero: string;
  total: number;
  emitida_en: string | null;
  url_pdf: string | null;
}

export interface ResumenReporte {
  desde: string;
  hasta: string;
  total_vendido: number;
  numero_ventas: number;
  ticket_promedio: number;
  top_productos: { nombre: string; cantidad: number; total: number }[];
}

export type TipoNotificacion = "STOCK_BAJO" | "CIERRE_CAJA" | "SISTEMA";

export interface Notificacion {
  id: number;
  tipo: TipoNotificacion;
  titulo: string;
  mensaje: string;
  leida: boolean;
  created_at: string | null;
}
