// Adaptador: implementa categorias.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { Categoria, EdicionCategoria, NuevaCategoria } from "../types";
import type { CategoriasPort } from "./categorias.port";

export const categoriasHttpAdapter: CategoriasPort = {
  async listar() {
    const { data } = await httpClient.get<Categoria[]>("/categorias");
    return data;
  },
  async crear(datos: NuevaCategoria) {
    const { data } = await httpClient.post<Categoria>("/categorias", datos);
    return data;
  },
  async editar(id, datos: EdicionCategoria) {
    const { data } = await httpClient.patch<Categoria>(`/categorias/${id}`, datos);
    return data;
  },
};
