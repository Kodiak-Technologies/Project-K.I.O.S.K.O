// Hook: abrir/cerrar caja y consultar el historial de turnos.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { cajaHttpAdapter } from "../services/caja.http-adapter";
import type { TurnoCaja } from "../types";

export function useCaja() {
  const [turno, setTurno] = useState<TurnoCaja | null>(null);
  const [turnos, setTurnos] = useState<TurnoCaja[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  // `cargando` es solo para la primera carga; las recargas son silenciosas.
  const recargar = useCallback(async () => {
    setError(null);
    try {
      const [actual, historial] = await Promise.all([
        cajaHttpAdapter.turnoActual(),
        cajaHttpAdapter.turnos(),
      ]);
      setTurno(actual);
      setTurnos(historial);
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

  const abrir = useCallback(
    async (montoInicial: number) => {
      setTurno(await cajaHttpAdapter.abrir(montoInicial));
      await recargar();
    },
    [recargar]
  );

  const cerrar = useCallback(
    async (montoFinal: number) => {
      setTurno(await cajaHttpAdapter.cerrar(montoFinal));
      await recargar();
    },
    [recargar]
  );

  return { turno, turnos, cargando, error, noDisponible, recargar, abrir, cerrar };
}
