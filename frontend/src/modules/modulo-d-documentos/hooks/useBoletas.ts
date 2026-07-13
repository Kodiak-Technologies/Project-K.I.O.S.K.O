// Hook: consultar/descargar boletas generadas.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { boletasHttpAdapter } from "../services/boletas.http-adapter";
import type { Boleta } from "../types";

export function useBoletas() {
  const [boletas, setBoletas] = useState<Boleta[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (desde?: string, hasta?: string) => {
    setCargando(true);
    setError(null);
    try {
      setBoletas(await boletasHttpAdapter.listar(desde, hasta));
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

  return { boletas, cargando, error, noDisponible, recargar };
}
