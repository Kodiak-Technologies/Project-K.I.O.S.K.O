// Adaptador: implementa categorias.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { CategoriasPort } from "./categorias.port";

export const categoriasHttpAdapter: CategoriasPort = {
  async listar() {
    const { data } = await httpClient.get("/categorias");
    return data;
  },
  async crear(nombre) {
    const { data } = await httpClient.post("/categorias", { nombre });
    return data;
  },
};
