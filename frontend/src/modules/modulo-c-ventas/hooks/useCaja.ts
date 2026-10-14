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
  // El historial NO se carga acá: depende de la fecha elegida y lo pide
  // `cargarHistorial` desde la pantalla.
  const recargar = useCallback(async () => {
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

  // El historial depende de la fecha elegida: se pide al backend el día exacto.
  // Antes el listado traía solo los últimos turnos y, al filtrar por una fecha
  // antigua en el cliente, esa fecha quedaba vacía porque no estaba incluida.
  const cargarHistorial = useCallback(async (desde?: string, hasta?: string) => {
    setError(null);
    try {
      setTurnos(await cajaHttpAdapter.turnos(undefined, desde, hasta));
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    }
  }, []);

  const abrir = useCallback(
    async (montoInicial: number) => {
      setTurno(await cajaHttpAdapter.abrir(montoInicial));
      await recargar();
    },
    [recargar]
  );

  const cerrar = useCallback(
    async (montoFinal: number, comentario?: string) => {
      const cerrado = await cajaHttpAdapter.cerrar(montoFinal, comentario);
      await recargar();
      return cerrado;
    },
    [recargar]
  );

  const editar = useCallback(
    async (turnoId: number, datos: { asignado_a_id?: number | null; monto_inicial?: number }) => {
      const editado = await cajaHttpAdapter.editar(turnoId, datos);
      await recargar();
      return editado;
    },
    [recargar]
  );

  return {
    turno,
    turnos,
    cargando,
    error,
    noDisponible,
    recargar,
    cargarHistorial,
    abrir,
    cerrar,
    editar,
  };
}
