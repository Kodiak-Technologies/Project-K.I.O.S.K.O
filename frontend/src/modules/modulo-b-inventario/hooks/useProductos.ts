// Hook: listar/crear/actualizar productos (y cambio de precio / historial).
//
// PR3a: `listar` ahora devuelve una respuesta paginada; el hook expone
// `productos` (items aplanados, para mantener compat con las páginas actuales)
// y `paginados` (respuesta cruda, para PR3b). `recargar` acepta filtros.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { useFiltrosEstables } from "../../../shared/lib/use-filtros-estables";
import { productosHttpAdapter } from "../services/productos.http-adapter";
import type {
  AjusteStock,
  AjusteStockRespuesta,
  BajaProducto,
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
  /** Suma/descuenta stock a mano (solo ADMIN; exige contraseña). */
  ajustarStock: (id: number, datos: AjusteStock) => Promise<AjusteStockRespuesta>;
  /** Baja lógica del producto (solo ADMIN; exige contraseña). */
  eliminar: (id: number, datos: BajaProducto) => Promise<Producto>;
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
  const { clave: filtrosKey, ref: filtrosRef } = useFiltrosEstables(filtrosIniciales);
  const recargar = useCallback(
    async (filtros?: FiltrosProductos) => {
      setError(null);
      try {
        const resp = await productosHttpAdapter.listar(filtros ?? filtrosRef.current);
        setPaginados(resp);
        setProductos(resp.items);
      } catch (e) {
        if (servicioNoDisponible(e)) setNoDisponible(true);
        else setError(mensajeDeError(e));
      } finally {
        setCargando(false);
      }
    },
    [filtrosRef]
  );

  useEffect(() => {
    void recargar(filtrosRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recargar, filtrosKey]);

  const crear = useCallback(
    async (datos: NuevoProducto) => {
      const creado = await productosHttpAdapter.crear(datos);
      await recargar(filtrosRef.current);
      return creado;
    },
    [recargar, filtrosRef]
  );

  const actualizar = useCallback(
    async (id: number, datos: EdicionProducto) => {
      const actualizado = await productosHttpAdapter.actualizar(id, datos);
      await recargar(filtrosRef.current);
      return actualizado;
    },
    [recargar, filtrosRef]
  );

  const cambiarPrecio = useCallback(
    async (id: number, datos: CambioPrecio) => productosHttpAdapter.cambiarPrecio(id, datos),
    []
  );

  const ajustarStock = useCallback(
    async (id: number, datos: AjusteStock) => {
      const respuesta = await productosHttpAdapter.ajustarStock(id, datos);
      await recargar(filtrosRef.current);
      return respuesta;
    },
    [recargar, filtrosRef]
  );

  const eliminar = useCallback(
    async (id: number, datos: BajaProducto) => {
      const eliminado = await productosHttpAdapter.eliminar(id, datos);
      await recargar(filtrosRef.current);
      return eliminado;
    },
    [recargar, filtrosRef]
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
    ajustarStock,
    eliminar,
    porReponer,
    historialPrecios,
  };
}
