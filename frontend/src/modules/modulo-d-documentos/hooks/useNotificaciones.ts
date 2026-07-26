// Hook: consultar historial y configuración de notificaciones.
import { useCallback, useEffect, useRef, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { notificacionesHttpAdapter } from "../services/notificaciones.http-adapter";
import type {
  ConfigNotificaciones,
  Notificacion,
  NotificacionesPaginadas,
} from "../types";

export function useNotificaciones() {
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  /** Respuesta paginada cruda: alimenta los controles de la tabla. */
  const [paginados, setPaginados] = useState<NotificacionesPaginadas | null>(null);
  const [config, setConfig] = useState<ConfigNotificaciones | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // `cargando` es solo para la primera carga; las recargas son silenciosas
  // (la campanita de la TopBar recarga cada vez que se abre).
  const recargar = useCallback(async (page = 1, pageSize = 20) => {
    setError(null);
    try {
      const resp = await notificacionesHttpAdapter.listar(page, pageSize);
      setPaginados(resp);
      setNotificaciones(resp.items);
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
    (nuevaConfig: Partial<ConfigNotificaciones>) => {
      setConfig((prev) => (prev ? { ...prev, ...nuevaConfig } : prev));
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(async () => {
        const resultado = await notificacionesHttpAdapter.actualizarConfig(nuevaConfig);
        setConfig(resultado);
      }, 500);
    },
    []
  );

  return { notificaciones, paginados, config, cargando, error, noDisponible, recargar, marcarLeida, actualizarConfig };
}
