// Hook: consultar la bitácora de movimientos de inventario.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { movimientosHttpAdapter } from "../services/movimientos.http-adapter";
import type { FiltrosMovimientos, MovimientoInventario, PaginadosResponse } from "../types";

interface EstadoHook {
  movimientos: MovimientoInventario[];
  paginados: PaginadosResponse<MovimientoInventario> | null;
  cargando: boolean;
  error: string | null;
  noDisponible: boolean;
  recargar: (filtros?: FiltrosMovimientos) => Promise<void>;
}

export function useMovimientos(filtrosIniciales?: FiltrosMovimientos): EstadoHook {
  const [movimientos, setMovimientos] = useState<MovimientoInventario[]>([]);
  const [paginados, setPaginados] = useState<PaginadosResponse<MovimientoInventario> | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (filtros?: FiltrosMovimientos) => {
    setError(null);
    try {
      const resp = await movimientosHttpAdapter.listar(filtros);
      setPaginados(resp);
      setMovimientos(resp.items);
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar(filtrosIniciales);
  }, [recargar, filtrosIniciales]);

  return { movimientos, paginados, cargando, error, noDisponible, recargar };
}
