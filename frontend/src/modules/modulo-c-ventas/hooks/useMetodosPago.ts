// Hook: catálogo de métodos de pago (activos para el POS; todos para el ADMIN).
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { metodosPagoHttpAdapter } from "../services/metodos-pago.http-adapter";
import type { MetodoPagoInfo } from "../types";

export function useMetodosPago(todos = false) {
  const [metodos, setMetodos] = useState<MetodoPagoInfo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async () => {
    setError(null);
    try {
      setMetodos(await metodosPagoHttpAdapter.listar(todos));
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, [todos]);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const crear = useCallback(
    async (datos: { codigo: string; nombre: string; es_efectivo: boolean }) => {
      await metodosPagoHttpAdapter.crear(datos);
      await recargar();
    },
    [recargar]
  );

  const actualizar = useCallback(
    async (id: number, cambios: { nombre?: string; activo?: boolean }) => {
      await metodosPagoHttpAdapter.actualizar(id, cambios);
      await recargar();
    },
    [recargar]
  );

  return { metodos, cargando, error, noDisponible, recargar, crear, actualizar };
}
