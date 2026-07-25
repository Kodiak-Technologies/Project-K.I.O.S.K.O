// Hook: registrar, aprobar y rechazar ingresos de mercadería.
//
// PR3a: `solicitar` ahora recibe `NuevaSolicitudIngreso` (proveedor + foto +
// líneas). `listar` devuelve respuesta paginada; el hook expone `ingresos`
// (items aplanados, compat con páginas actuales) y `paginados` (cruda).
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { ingresosHttpAdapter } from "../services/ingresos.http-adapter";
import type {
  AprobacionIngreso,
  FiltrosIngresos,
  NuevaSolicitudIngreso,
  PaginadosResponse,
  RechazoIngreso,
  SolicitudIngreso,
  SolicitudIngresoUpdateBody,
} from "../types";

interface EstadoHook {
  ingresos: SolicitudIngreso[];
  paginados: PaginadosResponse<SolicitudIngreso> | null;
  cargando: boolean;
  error: string | null;
  noDisponible: boolean;
  recargar: (filtros?: FiltrosIngresos) => Promise<void>;
  obtener: (id: number) => Promise<SolicitudIngreso>;
  solicitar: (datos: NuevaSolicitudIngreso) => Promise<SolicitudIngreso>;
  aprobar: (id: number) => Promise<AprobacionIngreso>;
  rechazar: (id: number, datos: RechazoIngreso) => Promise<SolicitudIngreso>;
  editar: (id: number, body: SolicitudIngresoUpdateBody) => Promise<SolicitudIngreso>;
}

export function useIngresos(filtrosIniciales?: FiltrosIngresos): EstadoHook {
  const [ingresos, setIngresos] = useState<SolicitudIngreso[]>([]);
  const [paginados, setPaginados] = useState<PaginadosResponse<SolicitudIngreso> | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (filtros?: FiltrosIngresos) => {
    setError(null);
    try {
      const resp = await ingresosHttpAdapter.listar(filtros);
      setPaginados(resp);
      setIngresos(resp.items);
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar(filtrosIniciales);
  }, [recargar, filtrosIniciales]);

  const obtener = useCallback(async (id: number) => {
    return ingresosHttpAdapter.obtener(id);
  }, []);

  const solicitar = useCallback(
    async (datos: NuevaSolicitudIngreso) => {
      const creada = await ingresosHttpAdapter.solicitar(datos);
      await recargar(filtrosIniciales);
      return creada;
    },
    [recargar, filtrosIniciales]
  );

  const aprobar = useCallback(
    async (id: number) => {
      const resp = await ingresosHttpAdapter.aprobar(id);
      await recargar(filtrosIniciales);
      return resp;
    },
    [recargar, filtrosIniciales]
  );

  const rechazar = useCallback(
    async (id: number, datos: RechazoIngreso) => {
      const resp = await ingresosHttpAdapter.rechazar(id, datos);
      await recargar(filtrosIniciales);
      return resp;
    },
    [recargar, filtrosIniciales]
  );

  const editar = useCallback(
    async (id: number, body: SolicitudIngresoUpdateBody) => {
      const actualizada = await ingresosHttpAdapter.editar(id, body);
      await recargar(filtrosIniciales);
      return actualizada;
    },
    [recargar, filtrosIniciales]
  );

  return {
    ingresos,
    paginados,
    cargando,
    error,
    noDisponible,
    recargar,
    obtener,
    solicitar,
    aprobar,
    rechazar,
    editar,
  };
}
