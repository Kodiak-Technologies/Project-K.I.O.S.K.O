import { httpClient } from "../../../shared/lib/http-client";
import type { RespaldosPort } from "./respaldos.port";

export const respaldosHttpAdapter: RespaldosPort = {
  async listar(page = 1, pageSize = 20) {
    const { data } = await httpClient.get("/respaldos", {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  async descargar(id) {
    const { data } = await httpClient.get(`/respaldos/${id}/descargar`, {
      responseType: "blob",
    });
    return data;
  },
};
