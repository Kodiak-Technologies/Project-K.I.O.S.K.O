// Tipos/DTOs del módulo de ventas (contrato esperado del backend de Clever).

export interface TurnoCaja {
  id: number;
  abierto_por: string;
  monto_inicial: number;
  monto_final: number | null;
  abierto_en: string;
  cerrado_en: string | null;
  estado: "ABIERTO" | "CERRADO";
  /** Quién cerró el turno (puede ser otro cajero en un cambio de turno). */
  cerrado_por: string | null;
}

export interface ItemVenta {
  producto_id: number;
  nombre: string;
  precio_unitario: number;
  cantidad: number;
}

/** Código de método de pago: los del catálogo (el ADMIN puede agregar más) o MIXTO. */
export type MetodoPago = string;

/** Método de pago del catálogo (gestionable por el ADMIN, RF-20). */
export interface MetodoPagoInfo {
  id: number;
  codigo: string;
  nombre: string;
  /** true = dinero físico que entra al cajón (cuenta para el arqueo). */
  es_efectivo: boolean;
  activo: boolean;
}

/** Una parte del pago (una venta mixta tiene varias). */
export interface PagoVenta {
  metodo: string;
  monto: number;
  es_efectivo: boolean;
  monto_recibido: number | null;
  vuelto: number;
}

export interface Venta {
  id: number;
  items: ItemVenta[];
  total: number;
  metodo_pago: MetodoPago;
  pagos: PagoVenta[];
  vuelto: number;
  vendedor: string;
  anulada: boolean;
  estado: "COMPLETADA" | "ANULADA" | "DEVUELTA_PARCIAL";
  turno_id: number;
  created_at: string | null;
}

export interface NuevoPago {
  metodo: string;
  /** Omitir en pago único: el backend lo completa con el total. */
  monto?: number;
  /** Solo efectivo: con cuánto paga el cliente (para el vuelto). */
  monto_recibido?: number;
}

export interface NuevaVenta {
  items: { producto_id: number; cantidad: number }[];
  pagos: NuevoPago[];
}
