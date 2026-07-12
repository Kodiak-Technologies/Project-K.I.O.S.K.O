// Puerto: QUÉ operaciones de autenticación existen, sin saber cómo se implementan.
// Componentes y hooks dependen de esta interfaz, nunca del adaptador concreto.
import type { TokenResponse, Usuario } from "../types";

export interface AuthPort {
  login(username: string, password: string): Promise<TokenResponse>;
  refresh(refreshToken: string): Promise<TokenResponse>;
  logout(refreshToken: string): Promise<void>;
  me(): Promise<Usuario>;
  cambiarPassword(passwordActual: string, passwordNueva: string): Promise<void>;
}
