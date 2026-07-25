// Tipos/DTOs del módulo de documentos.

export interface NotaVenta {
  venta_id: number;
  identificacion: string;
  fecha: string;
  total: number;
  metodo_pago: string;
  estado: string;
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

export type TipoNotificacion = "STOCK_BAJO" | "APERTURA_CAJA" | "CIERRE_CAJA" | "SOLICITUD_INGRESO" | "SISTEMA";

export interface Notificacion {
  id: number;
  tipo: TipoNotificacion;
  titulo: string;
  mensaje: string;
  leida: boolean;
  usuario_id: number | null;
  producto_id: number | null;
  created_at: string | null;
}

export interface ConfigNotificaciones {
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
  usuario_id: number | null;
  drive_file_id: string | null;
}
