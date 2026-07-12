// Adaptador: implementa ConfiguracionPort contra la API real.
import { httpClient } from "../../../shared/lib/http-client";
import type { Configuracion } from "../types";
import type { ConfiguracionPort } from "./configuracion.port";

export const configuracionHttpAdapter: ConfiguracionPort = {
  async obtener() {
    const { data } = await httpClient.get<Configuracion>("/configuracion");
    return data;
  },
  async actualizar(cambios) {
    const { data } = await httpClient.patch<Configuracion>("/configuracion", cambios);
    return data;
  },
  async subirLogo(archivo: File) {
    const formulario = new FormData();
    formulario.append("archivo", archivo);
    const { data } = await httpClient.post<Configuracion>("/configuracion/logo", formulario);
    return data;
  },
};
