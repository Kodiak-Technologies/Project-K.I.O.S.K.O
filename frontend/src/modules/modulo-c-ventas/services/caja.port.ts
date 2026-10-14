// Puerto: interfaz de apertura/cierre de caja.
import type { MovimientosTurno, ResumenCaja, TurnoCaja } from "../types";

export interface CajaPort {
  turnoActual(): Promise<TurnoCaja | null>;
  abrir(monto_inicial: number): Promise<TurnoCaja>;
  /** Sugerencia de cierre del turno abierto (efectivo esperado + desglose). */
  resumen(): Promise<ResumenCaja>;
  /** comentario obligatorio si monto_final difiere de la sugerencia. */
  cerrar(monto_final: number, comentario?: string): Promise<TurnoCaja>;
  /** Historial de turnos (visible para todos: cajeros y admin). Con `desde`/`hasta`
   * (YYYY-MM-DD) acota a los turnos de esa fecha; sin ellos, los más recientes. */
  turnos(limite?: number, desde?: string, hasta?: string): Promise<TurnoCaja[]>;
  /** Edita los detalles del turno (ej. usuario asignado o monto inicial). */
  editar(turnoId: number, datos: { asignado_a_id?: number | null; monto_inicial?: number }): Promise<TurnoCaja>;
  /** El rastro de un turno: ventas y anulaciones/devoluciones. */
  movimientos(turnoId: number): Promise<MovimientosTurno>;
}
