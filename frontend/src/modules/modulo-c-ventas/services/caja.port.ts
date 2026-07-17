// Puerto: interfaz de apertura/cierre de caja.
import type { MovimientosTurno, ResumenCaja, TurnoCaja } from "../types";

export interface CajaPort {
  turnoActual(): Promise<TurnoCaja | null>;
  abrir(monto_inicial: number): Promise<TurnoCaja>;
  /** Sugerencia de cierre del turno abierto (efectivo esperado + desglose). */
  resumen(): Promise<ResumenCaja>;
  /** comentario obligatorio si monto_final difiere de la sugerencia. */
  cerrar(monto_final: number, comentario?: string): Promise<TurnoCaja>;
  /** Historial de turnos (visible para todos: cajeros y admin). */
  turnos(limite?: number): Promise<TurnoCaja[]>;
  /** El rastro de un turno: ventas, anulaciones/devoluciones y abonos. */
  movimientos(turnoId: number): Promise<MovimientosTurno>;
}
