// Puerto: interfaz de apertura/cierre de caja.
import type { TurnoCaja } from "../types";

export interface CajaPort {
  turnoActual(): Promise<TurnoCaja | null>;
  abrir(monto_inicial: number): Promise<TurnoCaja>;
  cerrar(monto_final: number): Promise<TurnoCaja>;
}
