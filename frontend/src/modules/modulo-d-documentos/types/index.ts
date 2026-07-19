// Tipos/DTOs del módulo de documentos (contrato esperado del backend de Fabrizio).

export interface Boleta {
  id: number;
  venta_id: number;
  numero: string;
  total: number;
  emitida_en: string | null;
  url_pdf: string | null;
  cliente_nombre: string | null;
}

export interface ResumenReporte {
  desde: string;
  hasta: string;
  total_vendido: number;
  total_egresos: number;
  numero_ventas: number;
  ticket_promedio: number;
  top_productos: TopProducto[];
  metodos_pago: Record<string, number>;
}

export interface TopProducto {
  nombre: string;
  cantidad: number;
  total: number;
}

export type TipoNotificacion = "STOCK_BAJO" | "CIERRE_CAJA" | "SOLICITUD_INGRESO" | "SISTEMA";

export interface Notificacion {
  id: number;
  tipo: TipoNotificacion;
  titulo: string;
  mensaje: string;
  leida: boolean;
  created_at: string | null;
}

export interface ConfigNotificaciones {
  canal_telegram_activo: boolean;
  canal_correo_activo: boolean;
  nivel_detalle: "BAJO" | "ALTO";
}

export type EstadoRespaldo = "PENDIENTE" | "COMPLETADO" | "FALLIDO";

export interface Respaldo {
  id: number;
  archivo_nombre: string;
  tamano_bytes: number;
  estado: EstadoRespaldo;
  generado_en: string | null;
  expira_en: string | null;
}
