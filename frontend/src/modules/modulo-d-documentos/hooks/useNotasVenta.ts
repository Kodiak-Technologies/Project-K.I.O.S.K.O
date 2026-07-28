// Hook: consultar/descargar notas de venta generadas.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { notasVentaHttpAdapter } from "../services/notasVenta.http-adapter";
import type { FiltrosNotasVenta, NotaVenta, NotasVentaPaginadas } from "../types";

export function useNotasVenta() {
  const [notas, setNotas] = useState<NotaVenta[]>([]);
  /** Respuesta paginada cruda: alimenta los controles de la tabla. */
  const [paginados, setPaginados] = useState<NotasVentaPaginadas | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (filtros?: FiltrosNotasVenta) => {
    setCargando(true);
    setError(null);
    try {
      const resp = await notasVentaHttpAdapter.listar(filtros);
      setPaginados(resp);
      setNotas(resp.items);
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

  return { notas, paginados, cargando, error, noDisponible, recargar };
}
