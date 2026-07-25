// Hook: consultar/descargar notas de venta generadas.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { notasVentaHttpAdapter } from "../services/notasVenta.http-adapter";
import type { NotaVenta } from "../types";

export function useNotasVenta() {
  const [notas, setNotas] = useState<NotaVenta[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (desde?: string, hasta?: string) => {
    setCargando(true);
    setError(null);
    try {
      setNotas(await notasVentaHttpAdapter.listar(desde, hasta));
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  return { notas, cargando, error, noDisponible, recargar };
}
