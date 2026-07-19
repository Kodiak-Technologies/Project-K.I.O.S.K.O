// Hook: listar/crear/actualizar productos (y cambio de precio / historial).
//
// PR3a: `listar` ahora devuelve una respuesta paginada; el hook expone
// `productos` (items aplanados, para mantener compat con las páginas actuales)
// y `paginados` (respuesta cruda, para PR3b). `recargar` acepta filtros.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { productosHttpAdapter } from "../services/productos.http-adapter";
import type {
  CambioPrecio,
  CambioPrecioRespuesta,
  EdicionProducto,
  FiltrosProductos,
  HistorialPrecioItem,
  NuevoProducto,
  PaginadosResponse,
  PorReponerItem,
  Producto,
} from "../types";

interface EstadoHook {
  /** Items aplanados de la última respuesta paginada. */
  productos: Producto[];
  /** Respuesta paginada cruda del backend. */
  paginados: PaginadosResponse<Producto> | null;
  cargando: boolean;
  error: string | null;
  noDisponible: boolean;
  recargar: (filtros?: FiltrosProductos) => Promise<void>;
  crear: (datos: NuevoProducto) => Promise<Producto>;
  actualizar: (id: number, datos: EdicionProducto) => Promise<Producto>;
  cambiarPrecio: (id: number, datos: CambioPrecio) => Promise<CambioPrecioRespuesta>;
  porReponer: (filtros?: { categoria_id?: number; page?: number; page_size?: number }) => Promise<PaginadosResponse<PorReponerItem>>;
  historialPrecios: (
    id: number,
    filtros?: { tipo?: string; page?: number; page_size?: number }
  ) => Promise<PaginadosResponse<HistorialPrecioItem>>;
}

export function useProductos(filtrosIniciales?: FiltrosProductos): EstadoHook {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [paginados, setPaginados] = useState<PaginadosResponse<Producto> | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  // `cargando` es solo para la primera carga; las recargas son silenciosas.
  const recargar = useCallback(async (filtros?: FiltrosProductos) => {
    setError(null);
    try {
      const resp = await productosHttpAdapter.listar(filtros);
      setPaginados(resp);
      setProductos(resp.items);
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

  const crear = useCallback(
    async (datos: NuevoProducto) => {
      const creado = await productosHttpAdapter.crear(datos);
      await recargar(filtrosIniciales);
      return creado;
    },
    [recargar, filtrosIniciales]
  );

  const actualizar = useCallback(
    async (id: number, datos: EdicionProducto) => {
      const actualizado = await productosHttpAdapter.actualizar(id, datos);
      await recargar(filtrosIniciales);
      return actualizado;
    },
    [recargar, filtrosIniciales]
  );

  const cambiarPrecio = useCallback(
    async (id: number, datos: CambioPrecio) => productosHttpAdapter.cambiarPrecio(id, datos),
    []
  );

  const porReponer = useCallback(
    (filtros?: { categoria_id?: number; page?: number; page_size?: number }) =>
      productosHttpAdapter.porReponer(filtros),
    []
  );

  const historialPrecios = useCallback(
    (id: number, filtros?: { tipo?: string; page?: number; page_size?: number }) =>
      productosHttpAdapter.historialPrecios(id, filtros),
    []
  );

  return {
    productos,
    paginados,
    cargando,
    error,
    noDisponible,
    recargar,
    crear,
    actualizar,
    cambiarPrecio,
    porReponer,
    historialPrecios,
  };
}
