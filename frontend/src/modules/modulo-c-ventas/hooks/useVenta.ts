// Hook: registrar/anular ventas y consultar historial.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { ventasHttpAdapter } from "../services/ventas.http-adapter";
import type { NuevaVenta, Venta, VentasPaginadas } from "../types";

export function useVenta() {
  const [ventas, setVentas] = useState<Venta[]>([]);
  /** Respuesta paginada cruda: alimenta los controles de la tabla. */
  const [paginados, setPaginados] = useState<VentasPaginadas | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  // `cargando` es solo para la primera carga; las recargas son silenciosas.
  const recargar = useCallback(
    async (desde?: string, hasta?: string, page = 1, pageSize = 20) => {
    setError(null);
    try {
      const resp = await ventasHttpAdapter.listar(desde, hasta, page, pageSize);
      setPaginados(resp);
      setVentas(resp.items);
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

  const registrar = useCallback(async (venta: NuevaVenta) => {
    return await ventasHttpAdapter.registrar(venta);
  }, []);

  const anular = useCallback(
    async (id: number, motivo: string) => {
      await ventasHttpAdapter.anular(id, motivo);
      await recargar();
    },
    [recargar]
  );

  const devolver = useCallback(
    async (id: number, items: { detalle_id: number; cantidad: number }[], motivo: string) => {
      await ventasHttpAdapter.devolver(id, items, motivo);
      await recargar();
    },
    [recargar]
  );

  return { ventas, paginados, cargando, error, noDisponible, recargar, registrar, anular, devolver };
}
