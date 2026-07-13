// Hook: generar/consultar reportes de ventas.
import { useCallback, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { reportesHttpAdapter } from "../services/reportes.http-adapter";
import type { ResumenReporte } from "../types";

export function useReportes() {
  const [resumen, setResumen] = useState<ResumenReporte | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const generar = useCallback(async (desde: string, hasta: string) => {
    setCargando(true);
    setError(null);
    try {
      setResumen(await reportesHttpAdapter.resumen(desde, hasta));
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  return { resumen, cargando, error, noDisponible, generar };
}
