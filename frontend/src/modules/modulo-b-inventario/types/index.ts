// Tipos/DTOs del módulo de inventario (contrato esperado del backend de Brayan).

export interface Categoria {
  id: number;
  nombre: string;
}

export interface Producto {
  id: number;
  codigo: string;
  nombre: string;
  categoria_id: number | null;
  categoria: string | null;
  precio: number;
  stock: number;
  stock_minimo: number;
  activo: boolean;
}

export type EstadoIngreso = "PENDIENTE" | "APROBADO" | "RECHAZADO";

export interface IngresoMercaderia {
  id: number;
  producto_id: number;
  producto: string;
  cantidad: number;
  estado: EstadoIngreso;
  solicitado_por: string;
  motivo_rechazo: string | null;
  created_at: string | null;
}

export interface NuevoProducto {
  codigo: string;
  nombre: string;
  categoria_id: number | null;
  precio: number;
  stock_minimo: number;
  /** Existencias con las que se da de alta (el flujo formal de reposición es el de ingresos). */
  stock_inicial?: number;
}
