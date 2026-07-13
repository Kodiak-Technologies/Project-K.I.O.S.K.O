// Hook: abrir/cerrar caja.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { cajaHttpAdapter } from "../services/caja.http-adapter";
import type { TurnoCaja } from "../types";

export function useCaja() {
  const [turno, setTurno] = useState<TurnoCaja | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setTurno(await cajaHttpAdapter.turnoActual());
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

  const abrir = useCallback(async (montoInicial: number) => {
    setTurno(await cajaHttpAdapter.abrir(montoInicial));
  }, []);

  const cerrar = useCallback(async (montoFinal: number) => {
    setTurno(await cajaHttpAdapter.cerrar(montoFinal));
  }, []);

  return { turno, cargando, error, noDisponible, recargar, abrir, cerrar };
}
