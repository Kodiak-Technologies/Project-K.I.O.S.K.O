// Adaptador: implementa productos.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { ProductosPort } from "./productos.port";

export const productosHttpAdapter: ProductosPort = {
  async listar(busqueda) {
    const { data } = await httpClient.get("/productos", { params: busqueda ? { q: busqueda } : undefined });
    return data;
  },
  async crear(datos) {
    const { data } = await httpClient.post("/productos", datos);
    return data;
  },
  async actualizar(id, datos) {
    const { data } = await httpClient.patch(`/productos/${id}`, datos);
    return data;
  },
};
