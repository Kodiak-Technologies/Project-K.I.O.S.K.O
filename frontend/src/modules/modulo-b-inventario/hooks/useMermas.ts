// Hook: listar, registrar, confirmar y rechazar mermas.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { mermasHttpAdapter } from "../services/mermas.http-adapter";
import type {
  ConfirmacionMerma,
  FiltrosMermas,
  Merma,
  NuevaMerma,
  PaginadosResponse,
  RechazoMerma,
} from "../types";

interface EstadoHook {
  mermas: Merma[];
  paginados: PaginadosResponse<Merma> | null;
  cargando: boolean;
  error: string | null;
  noDisponible: boolean;
  recargar: (filtros?: FiltrosMermas) => Promise<void>;
  registrar: (datos: NuevaMerma) => Promise<Merma>;
  confirmar: (id: number) => Promise<ConfirmacionMerma>;
  rechazar: (id: number, datos: RechazoMerma) => Promise<Merma>;
}

export function useMermas(filtrosIniciales?: FiltrosMermas): EstadoHook {
  const [mermas, setMermas] = useState<Merma[]>([]);
  const [paginados, setPaginados] = useState<PaginadosResponse<Merma> | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (filtros?: FiltrosMermas) => {
    setError(null);
    try {
      const resp = await mermasHttpAdapter.listar(filtros);
      setPaginados(resp);
      setMermas(resp.items);
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

  const registrar = useCallback(
    async (datos: NuevaMerma) => {
      const creada = await mermasHttpAdapter.crear(datos);
      await recargar(filtrosIniciales);
      return creada;
    },
    [recargar, filtrosIniciales]
  );

  const confirmar = useCallback(
    async (id: number) => {
      const resp = await mermasHttpAdapter.confirmar(id);
      await recargar(filtrosIniciales);
      return resp;
    },
    [recargar, filtrosIniciales]
  );

  const rechazar = useCallback(
    async (id: number, datos: RechazoMerma) => {
      const resp = await mermasHttpAdapter.rechazar(id, datos);
      await recargar(filtrosIniciales);
      return resp;
    },
    [recargar, filtrosIniciales]
  );

  return { mermas, paginados, cargando, error, noDisponible, recargar, registrar, confirmar, rechazar };
}
