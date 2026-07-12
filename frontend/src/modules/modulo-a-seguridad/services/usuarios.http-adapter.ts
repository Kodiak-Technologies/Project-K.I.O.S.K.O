// Adaptador: implementa UsuariosPort contra la API real.
import { httpClient } from "../../../shared/lib/http-client";
import type { Rol, Usuario } from "../types";
import type { CrearUsuarioInput, UsuariosPort } from "./usuarios.port";

export const usuariosHttpAdapter: UsuariosPort = {
  async listar() {
    const { data } = await httpClient.get<Usuario[]>("/usuarios");
    return data;
  },
  async crear(datos: CrearUsuarioInput) {
    const { data } = await httpClient.post<Usuario>("/usuarios", datos);
    return data;
  },
  async editar(id, datos) {
    const { data } = await httpClient.patch<Usuario>(`/usuarios/${id}`, datos);
    return data;
  },
  async cambiarEstado(id, activo) {
    const { data } = await httpClient.patch<Usuario>(`/usuarios/${id}/estado`, { activo });
    return data;
  },
  async eliminar(id, motivo) {
    await httpClient.delete(`/usuarios/${id}`, { data: motivo ? { motivo } : undefined });
  },
  async resetearPassword(id, passwordNueva, forzarCambio) {
    await httpClient.patch(`/usuarios/${id}/password`, {
      password_nueva: passwordNueva,
      forzar_cambio: forzarCambio,
    });
  },
  async listarRoles() {
    const { data } = await httpClient.get<Rol[]>("/roles");
    return data;
  },
};
