import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { respaldosHttpAdapter } from "../services/respaldos.http-adapter";
import type { Respaldo } from "../types";

export function useRespaldos() {
  const [respaldos, setRespaldos] = useState<Respaldo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setRespaldos(await respaldosHttpAdapter.listar());
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

  const crear = useCallback(async () => {
    try {
      await respaldosHttpAdapter.crear();
      await recargar();
    } catch (e) {
      setError(mensajeDeError(e));
    }
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

  const restaurar = useCallback(async (id: number) => {
    try {
      await respaldosHttpAdapter.restaurar(id);
      await recargar();
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }, [recargar]);

  return { respaldos, cargando, error, noDisponible, recargar, crear, descargar, restaurar };
}
