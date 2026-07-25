// Adaptador: implementa ingresos.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type {
  AprobacionIngreso,
  FiltrosIngresos,
  NuevaSolicitudIngreso,
  PaginadosResponse,
  RechazoIngreso,
  SolicitudIngreso,
  SolicitudIngresoUpdateBody,
} from "../types";
import type { IngresosPort } from "./ingresos.port";

function limpiarParams(params: object | undefined): Record<string, unknown> | undefined {
  if (!params) return undefined;
  const limpio: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") limpio[k] = v;
  }
  return Object.keys(limpio).length > 0 ? limpio : undefined;
}

export const ingresosHttpAdapter: IngresosPort = {
  async listar(filtros) {
    const { data } = await httpClient.get<PaginadosResponse<SolicitudIngreso>>("/ingresos", {
      params: limpiarParams(filtros),
    });
    return data;
  },
  async obtener(id) {
    const { data } = await httpClient.get<SolicitudIngreso>(`/ingresos/${id}`);
    return data;
  },
  async obtenerPorId(id) {
    const { data } = await httpClient.get<SolicitudIngreso>(`/ingresos/${id}`);
    return data;
  },
  async solicitar(datos: NuevaSolicitudIngreso) {
    const { data } = await httpClient.post<SolicitudIngreso>("/ingresos", datos);
    return data;
  },
  async aprobar(id) {
    const { data } = await httpClient.post<AprobacionIngreso>(`/ingresos/${id}/aprobar`);
    return data;
  },
  async rechazar(id, datos: RechazoIngreso) {
    const { data } = await httpClient.post<SolicitudIngreso>(`/ingresos/${id}/rechazar`, datos);
    return data;
  },
  async editar(id, body) {
    const { data } = await httpClient.patch<SolicitudIngreso>(`/ingresos/${id}`, body);
    return data;
  },
};
