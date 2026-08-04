// Hook: registrar, aprobar y rechazar ingresos de mercadería.
//
// PR3a: `solicitar` ahora recibe `NuevaSolicitudIngreso` (proveedor + foto +
// líneas). `listar` devuelve respuesta paginada; el hook expone `ingresos`
// (items aplanados, compat con páginas actuales) y `paginados` (cruda).
import { useCallback, useEffect, useRef, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { useFiltrosEstables } from "../../../shared/lib/use-filtros-estables";
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

  // Últimos filtros con los que se pidió la lista. Las páginas (Aprobación,
  // Ingresos) NO pasan `filtrosIniciales`: arman los filtros ellas y los mandan
  // por `recargar(...)` cada vez que cambia la paginación o un filtro. Si las
  // recargas post-mutación usaran `filtrosIniciales`, pedirían la lista SIN
  // filtro: en Aprobación eso traía de vuelta la solicitud recién aprobada
  // (estado "Aprobada") a una cola que solo debe mostrar pendientes.
  const ultimosFiltros = useRef<FiltrosIngresos | undefined>(filtrosIniciales);

  const recargar = useCallback(async (filtros?: FiltrosIngresos) => {
    ultimosFiltros.current = filtros;
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

  /** Recarga repitiendo los filtros vigentes (tras crear/aprobar/rechazar/editar). */
  const revalidar = useCallback(() => recargar(ultimosFiltros.current), [recargar]);

  // El literal `{ page_size: 100 }` es un objeto nuevo en cada render: como
  // dependencia dispara el efecto en bucle. Dependemos de su CONTENIDO.
  const { clave: filtrosKey, ref: filtrosRef } = useFiltrosEstables(filtrosIniciales);

  useEffect(() => {
    void recargar(filtrosRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recargar, filtrosKey]);

  const obtener = useCallback(async (id: number) => {
    return ingresosHttpAdapter.obtener(id);
  }, []);

  const solicitar = useCallback(
    async (datos: NuevaSolicitudIngreso) => {
      const creada = await ingresosHttpAdapter.solicitar(datos);
      await revalidar();
      return creada;
    },
    [revalidar]
  );

  const aprobar = useCallback(
    async (id: number) => {
      const resp = await ingresosHttpAdapter.aprobar(id);
      await revalidar();
      return resp;
    },
    [revalidar]
  );

  const rechazar = useCallback(
    async (id: number, datos: RechazoIngreso) => {
      const resp = await ingresosHttpAdapter.rechazar(id, datos);
      await revalidar();
      return resp;
    },
    [revalidar]
  );

  const editar = useCallback(
    async (id: number, body: SolicitudIngresoUpdateBody) => {
      const actualizada = await ingresosHttpAdapter.editar(id, body);
      await revalidar();
      return actualizada;
    },
    [revalidar]
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
