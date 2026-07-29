import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { respaldosHttpAdapter } from "../services/respaldos.http-adapter";
import type { Respaldo, RespaldosPaginados } from "../types";

export function useRespaldos() {
  const [respaldos, setRespaldos] = useState<Respaldo[]>([]);
  /** Respuesta paginada cruda: alimenta los controles de la tabla. */
  const [paginados, setPaginados] = useState<RespaldosPaginados | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (page = 1, pageSize = 20) => {
    setCargando(true);
    setError(null);
    try {
      const resp = await respaldosHttpAdapter.listar(page, pageSize);
      setPaginados(resp);
      setRespaldos(resp.items);
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

  const descargar = useCallback(async (id: number, nombre: string) => {
    try {
      const blob = await respaldosHttpAdapter.descargar(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = nombre;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }, []);

  return { respaldos, paginados, cargando, error, noDisponible, recargar, descargar };
}
