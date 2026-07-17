import { httpClient } from "../../../shared/lib/http-client";
import type { RespaldosPort } from "./respaldos.port";

export const respaldosHttpAdapter: RespaldosPort = {
  async listar() {
    const { data } = await httpClient.get("/respaldos");
    return data;
  },

  async crear() {
    const { data } = await httpClient.post("/respaldos");
    return data;
  },

  async descargar(id) {
    const { data } = await httpClient.get(`/respaldos/${id}/descargar`, {
      responseType: "blob",
    });
    return data;
  },
};
