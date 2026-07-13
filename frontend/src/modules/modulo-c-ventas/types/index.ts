// Tipos/DTOs del módulo de ventas (contrato esperado del backend de Clever).

export interface TurnoCaja {
  id: number;
  abierto_por: string;
  monto_inicial: number;
  monto_final: number | null;
  abierto_en: string;
  cerrado_en: string | null;
  estado: "ABIERTO" | "CERRADO";
}

export interface ItemVenta {
  producto_id: number;
  nombre: string;
  precio_unitario: number;
  cantidad: number;
}

export type MetodoPago = "EFECTIVO" | "YAPE" | "PLIN" | "TARJETA";

export interface Venta {
  id: number;
  items: ItemVenta[];
  total: number;
  metodo_pago: MetodoPago;
  vendedor: string;
  anulada: boolean;
  created_at: string | null;
}

export interface NuevaVenta {
  items: { producto_id: number; cantidad: number }[];
  metodo_pago: MetodoPago;
}
