// Adaptador: implementa mermas.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type {
  ConfirmacionMerma,
  FiltrosMermas,
  Merma,
  NuevaMerma,
  PaginadosResponse,
  RechazoMerma,
} from "../types";
import type { MermasPort } from "./mermas.port";

function limpiarParams(params: object | undefined): Record<string, unknown> | undefined {
  if (!params) return undefined;
  const limpio: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") limpio[k] = v;
  }
  return Object.keys(limpio).length > 0 ? limpio : undefined;
}

export const mermasHttpAdapter: MermasPort = {
  async listar(filtros) {
    const { data } = await httpClient.get<PaginadosResponse<Merma>>("/mermas", {
      params: limpiarParams(filtros),
    });
    return data;
  },
  async obtener(id) {
    const { data } = await httpClient.get<Merma>(`/mermas/${id}`);
    return data;
  },
  async crear(datos: NuevaMerma) {
    const { data } = await httpClient.post<Merma>("/mermas", datos);
    return data;
  },
  async confirmar(id) {
    const { data } = await httpClient.post<ConfirmacionMerma>(`/mermas/${id}/confirmar`);
    return data;
  },
  async rechazar(id, datos: RechazoMerma) {
    const { data } = await httpClient.post<Merma>(`/mermas/${id}/rechazar`, datos);
    return data;
  },
};
