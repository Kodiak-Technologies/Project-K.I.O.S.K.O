// Hook: consultar la bitácora de movimientos de inventario.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { useFiltrosEstables } from "../../../shared/lib/use-filtros-estables";
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

  // El literal `{ page_size: 100 }` es un objeto nuevo en cada render: como
  // dependencia dispara el efecto en bucle. Dependemos de su CONTENIDO.
  const { clave: filtrosKey, ref: filtrosRef } = useFiltrosEstables(filtrosIniciales);

  useEffect(() => {
    void recargar(filtrosRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recargar, filtrosKey]);

  return { movimientos, paginados, cargando, error, noDisponible, recargar };
}
