// Adaptador: implementa productos.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
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
import type { ProductosPort } from "./productos.port";

/** Quita claves con `undefined`/`null`/`""` para no mandarlas como
 *  `?key=undefined` en la URL. Acepta cualquier objeto (con o sin index signature). */
function limpiarParams(params: object | undefined): Record<string, unknown> | undefined {
  if (!params) return undefined;
  const limpio: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") limpio[k] = v;
  }
  return Object.keys(limpio).length > 0 ? limpio : undefined;
}

export const productosHttpAdapter: ProductosPort = {
  async listar(filtros) {
    const { data } = await httpClient.get<PaginadosResponse<Producto>>("/productos", {
      params: limpiarParams(filtros),
    });
    return data;
  },
  async obtener(id) {
    const { data } = await httpClient.get<Producto>(`/productos/${id}`);
    return data;
  },
  async buscar(codigo, nombre, categoria_id) {
    const params = limpiarParams({ codigo, nombre, categoria_id });
    const { data } = await httpClient.get<Producto | Producto[]>("/productos/buscar", { params });
    return data;
  },
  async porReponer(filtros) {
    const { data } = await httpClient.get<PaginadosResponse<PorReponerItem>>(
      "/productos/por-reponer",
      { params: limpiarParams(filtros) }
    );
    return data;
  },
  async crear(datos: NuevoProducto) {
    const { data } = await httpClient.post<Producto>("/productos", datos);
    return data;
  },
  async actualizar(id, datos: EdicionProducto) {
    const { data } = await httpClient.patch<Producto>(`/productos/${id}`, datos);
    return data;
  },
  async cambiarPrecio(id, datos: CambioPrecio) {
    const { data } = await httpClient.patch<CambioPrecioRespuesta>(`/productos/${id}/precio`, datos);
    return data;
  },
  async historialPrecios(id, filtros) {
    const { data } = await httpClient.get<PaginadosResponse<HistorialPrecioItem>>(
      `/productos/${id}/historial-precios`,
      { params: limpiarParams(filtros) }
    );
    return data;
  },
};
