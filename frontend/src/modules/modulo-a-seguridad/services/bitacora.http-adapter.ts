// Adaptador: implementa BitacoraPort contra la API real.
import { httpClient } from "../../../shared/lib/http-client";
import type { BitacoraPaginada, FiltrosBitacora } from "../types";
import type { BitacoraPort } from "./bitacora.port";

export const bitacoraHttpAdapter: BitacoraPort = {
  async consultar(filtros: FiltrosBitacora) {
    const params = Object.fromEntries(
      Object.entries(filtros).filter(([, v]) => v !== undefined && v !== "")
    );
    const { data } = await httpClient.get<BitacoraPaginada>("/bitacora", { params });
    return data;
  },
};
