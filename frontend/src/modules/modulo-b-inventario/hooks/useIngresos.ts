// Hook: registrar, aprobar y rechazar ingresos de mercadería.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { ingresosHttpAdapter } from "../services/ingresos.http-adapter";
import type { IngresoMercaderia } from "../types";

export function useIngresos() {
  const [ingresos, setIngresos] = useState<IngresoMercaderia[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setIngresos(await ingresosHttpAdapter.listar());
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

  const solicitar = useCallback(
    async (producto_id: number, cantidad: number) => {
      await ingresosHttpAdapter.solicitar(producto_id, cantidad);
      await recargar();
    },
    [recargar]
  );

  const aprobar = useCallback(
    async (id: number) => {
      await ingresosHttpAdapter.aprobar(id);
      await recargar();
    },
    [recargar]
  );

  const rechazar = useCallback(
    async (id: number, motivo: string) => {
      await ingresosHttpAdapter.rechazar(id, motivo);
      await recargar();
    },
    [recargar]
  );

  return { ingresos, cargando, error, noDisponible, solicitar, aprobar, rechazar };
}
