// Puerto: interfaz de apertura/cierre de caja.
import type { TurnoCaja } from "../types";

export interface CajaPort {
  turnoActual(): Promise<TurnoCaja | null>;
  abrir(monto_inicial: number): Promise<TurnoCaja>;
  cerrar(monto_final: number): Promise<TurnoCaja>;
  /** Historial de turnos (visible para todos: cajeros y admin). */
  turnos(limite?: number): Promise<TurnoCaja[]>;
}
