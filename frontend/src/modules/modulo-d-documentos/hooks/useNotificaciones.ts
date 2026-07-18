// Hook: consultar historial y configuración de notificaciones.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { notificacionesHttpAdapter } from "../services/notificaciones.http-adapter";
import type { ConfigNotificaciones, Notificacion } from "../types";

export function useNotificaciones() {
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [config, setConfig] = useState<ConfigNotificaciones | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setNotificaciones(await notificacionesHttpAdapter.listar());
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  const recargarConfig = useCallback(async () => {
    try {
      setConfig(await notificacionesHttpAdapter.obtenerConfig());
    } catch {
    }
  }, []);

  useEffect(() => {
    void recargar();
    void recargarConfig();
  }, [recargar, recargarConfig]);

  const marcarLeida = useCallback(
    async (id: number) => {
      await notificacionesHttpAdapter.marcarLeida(id);
      await recargar();
    },
    [recargar]
  );

  const actualizarConfig = useCallback(
    async (nuevaConfig: Partial<ConfigNotificaciones>) => {
      const resultado = await notificacionesHttpAdapter.actualizarConfig(nuevaConfig);
      setConfig(resultado);
    },
    []
  );

  return { notificaciones, config, cargando, error, noDisponible, marcarLeida, actualizarConfig };
}
