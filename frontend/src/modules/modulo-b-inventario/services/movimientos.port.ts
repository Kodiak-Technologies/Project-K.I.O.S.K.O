// Puerto: interfaz de consulta de la bitácora de movimientos de inventario.
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/inventario_movimientos_router.py
import type { FiltrosMovimientos, MovimientoInventario, PaginadosResponse } from "../types";

export interface MovimientosPort {
  /** `GET /inventario/movimientos` (paginado, con filtros opcionales). */
  listar(filtros?: FiltrosMovimientos): Promise<PaginadosResponse<MovimientoInventario>>;
}
