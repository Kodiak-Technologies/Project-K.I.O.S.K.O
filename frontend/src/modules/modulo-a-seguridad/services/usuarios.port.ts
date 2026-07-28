// Puerto: operaciones de gestión de usuarios y roles (solo las usa el ADMIN).
import type { Rol, Usuario } from "../types";

export interface CrearUsuarioInput {
  username: string;
  nombre: string;
  password: string;
  rol_id: number;
  forzar_cambio_password: boolean;
}

export interface UsuariosPort {
  listar(): Promise<Usuario[]>;
  crear(datos: CrearUsuarioInput): Promise<Usuario>;
  editar(id: number, datos: { nombre?: string; rol_id?: number }): Promise<Usuario>;
  cambiarEstado(id: number, activo: boolean): Promise<Usuario>;
  eliminar(id: number, motivo?: string): Promise<void>;
  resetearPassword(id: number, passwordNueva: string, forzarCambio: boolean): Promise<void>;
  listarRoles(): Promise<Rol[]>;
}
