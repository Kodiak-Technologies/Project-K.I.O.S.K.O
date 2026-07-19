// Puerto: interfaz del catálogo de métodos de pago.
import type { MetodoPagoInfo } from "../types";

export interface MetodosPagoPort {
  listar(todos?: boolean): Promise<MetodoPagoInfo[]>;
  crear(datos: { codigo: string; nombre: string; es_efectivo: boolean }): Promise<MetodoPagoInfo>;
  actualizar(id: number, cambios: { nombre?: string; activo?: boolean }): Promise<MetodoPagoInfo>;
}
