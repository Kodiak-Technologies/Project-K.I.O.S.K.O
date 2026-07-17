// Tipos/DTOs del módulo de ventas (contrato esperado del backend de Clever).

/** Detalle del arqueo de un turno cerrado (RF-17). */
export interface Arqueo {
  efectivo_esperado: number;
  efectivo_contado: number;
  /** contado - esperado (negativo = faltante). */
  diferencia: number;
  /** Obligatorio cuando hubo descuadre: el admin lo revisa. */
  comentario: string | null;
  total_vendido: number;
  totales_por_metodo: Record<string, number>;
}

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
  /** Solo en turnos cerrados. */
  arqueo: Arqueo | null;
}

/** Sugerencia de cierre del turno abierto (GET /caja/resumen). */
export interface ResumenCaja {
  turno: TurnoCaja;
  efectivo_esperado: number;
  desglose: {
    monto_inicial: number;
    ventas_efectivo: number;
    abonos_efectivo: number;
    devoluciones_efectivo: number;
  };
  totales_por_metodo: Record<string, number>;
  total_vendido: number;
  numero_ventas: number;
}

export interface ItemVenta {
  producto_id: number;
  nombre: string;
  precio_unitario: number;
  cantidad: number;
  /** id de la línea en el backend (necesario para devoluciones parciales). */
  id?: number;
  cantidad_devuelta?: number;
}

/** El rastro de un reverso: anulación total o devolución parcial (RF-22). */
export interface Anulacion {
  id: number;
  venta_id: number;
  turno_id: number;
  tipo: "ANULACION" | "DEVOLUCION";
  realizado_por: string;
  motivo: string;
  monto: number;
  efectivo_devuelto: number;
  items: { producto_id: number; nombre: string; cantidad: number }[];
  created_at: string | null;
}

/** Rastro completo de un turno (modal del panel de caja del admin). */
export interface MovimientosTurno {
  ventas: Venta[];
  reversos: Anulacion[];
  abonos: Record<string, unknown>[];
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
