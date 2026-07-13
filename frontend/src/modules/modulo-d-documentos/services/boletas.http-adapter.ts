// Adaptador: implementa boletas.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { BoletasPort } from "./boletas.port";

export const boletasHttpAdapter: BoletasPort = {
  async listar(desde, hasta) {
    const { data } = await httpClient.get("/boletas", { params: { desde, hasta } });
    return data;
  },
};
