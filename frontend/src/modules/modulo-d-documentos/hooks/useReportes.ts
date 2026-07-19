// Hook: generar/consultar reportes de ventas.
import { useCallback, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { reportesHttpAdapter } from "../services/reportes.http-adapter";
import type { ResumenReporte, TopProducto } from "../types";

export function useReportes() {
  const [resumen, setResumen] = useState<ResumenReporte | null>(null);
  const [masVendidos, setMasVendidos] = useState<TopProducto[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const generar = useCallback(async (desde: string, hasta: string) => {
    setCargando(true);
    setError(null);
    try {
      setResumen(await reportesHttpAdapter.resumen(desde, hasta));
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  const generarMasVendidos = useCallback(
    async (desde: string, hasta: string, criterio: string, orden: string) => {
      setCargando(true);
      setError(null);
      try {
        setMasVendidos(await reportesHttpAdapter.masVendidos(desde, hasta, criterio, orden));
      } catch (e) {
        if (servicioNoDisponible(e)) setNoDisponible(true);
        else setError(mensajeDeError(e));
      } finally {
        setCargando(false);
      }
    },
    []
  );

  const exportar = useCallback(
    async (desde: string, hasta: string, tipo: string) => {
      try {
        const blob = await reportesHttpAdapter.exportar(desde, hasta, tipo);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `reporte_${tipo}_${desde}_${hasta}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (e) {
        setError(mensajeDeError(e));
      }
    },
    []
  );

  return { resumen, masVendidos, cargando, error, noDisponible, generar, generarMasVendidos, exportar };
}
