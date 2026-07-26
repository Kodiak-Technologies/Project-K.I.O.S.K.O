// Adaptador: implementa proveedores.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type {
  EdicionProveedor,
  FiltrosPagosProveedor,
  FiltrosProveedores,
  NuevoPagoProveedor,
  NuevoProveedor,
  PagosPaginadosResponse,
  PaginadosResponse,
  PagoProveedor,
  Proveedor,
} from "../types";
import type { ProveedoresPort } from "./proveedores.port";

function limpiarParams(params: object | undefined): Record<string, unknown> | undefined {
  if (!params) return undefined;
  const limpio: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") limpio[k] = v;
  }
  return Object.keys(limpio).length > 0 ? limpio : undefined;
}

export const proveedoresHttpAdapter: ProveedoresPort = {
  async listar(filtros) {
    const { data } = await httpClient.get<PaginadosResponse<Proveedor>>("/proveedores", {
      params: limpiarParams(filtros),
    });
    return data;
  },
  async obtener(id) {
    const { data } = await httpClient.get<Proveedor>(`/proveedores/${id}`);
    return data;
  },
  async crear(datos: NuevoProveedor) {
    const { data } = await httpClient.post<Proveedor>("/proveedores", datos);
    return data;
  },
  async editar(id, datos: EdicionProveedor) {
    const { data } = await httpClient.patch<Proveedor>(`/proveedores/${id}`, datos);
    return data;
  },
  async registrarCompraCredito(id, datos: NuevoPagoProveedor) {
    const { data } = await httpClient.post<PagoProveedor>(`/proveedores/${id}/compras-credito`, datos);
    return data;
  },
  async registrarPago(id, datos: NuevoPagoProveedor) {
    const { data } = await httpClient.post<PagoProveedor>(`/proveedores/${id}/pagos`, datos);
    return data;
  },
  async listarPagos(proveedorId, filtros) {
    const { data } = await httpClient.get<PagosPaginadosResponse>(
      `/proveedores/${proveedorId}/pagos`,
      { params: limpiarParams(filtros) }
    );
    return data;
  },
};
