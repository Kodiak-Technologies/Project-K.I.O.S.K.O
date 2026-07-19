// Adaptador: implementa movimientos.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { FiltrosMovimientos, MovimientoInventario, PaginadosResponse } from "../types";
import type { MovimientosPort } from "./movimientos.port";

function limpiarParams(params: object | undefined): Record<string, unknown> | undefined {
  if (!params) return undefined;
  const limpio: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") limpio[k] = v;
  }
  return Object.keys(limpio).length > 0 ? limpio : undefined;
}

export const movimientosHttpAdapter: MovimientosPort = {
  async listar(filtros) {
    const { data } = await httpClient.get<PaginadosResponse<MovimientoInventario>>(
      "/inventario/movimientos",
      { params: limpiarParams(filtros) }
    );
    return data;
  },
};
