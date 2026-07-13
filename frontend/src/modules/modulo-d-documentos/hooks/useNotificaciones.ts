// Hook: consultar historial y marcar notificaciones como leídas.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { notificacionesHttpAdapter } from "../services/notificaciones.http-adapter";
import type { Notificacion } from "../types";

export function useNotificaciones() {
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
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

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const marcarLeida = useCallback(
    async (id: number) => {
      await notificacionesHttpAdapter.marcarLeida(id);
      await recargar();
    },
    [recargar]
  );

  return { notificaciones, cargando, error, noDisponible, marcarLeida };
}
