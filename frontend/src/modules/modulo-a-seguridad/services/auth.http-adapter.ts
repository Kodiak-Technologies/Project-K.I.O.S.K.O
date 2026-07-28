// Adaptador: implementa AuthPort contra la API real. Si el contrato del backend
// cambia, SOLO se toca este archivo (los hooks y páginas no se enteran).
import { httpClient } from "../../../shared/lib/http-client";
import type { TokenResponse, Usuario } from "../types";
import type { AuthPort } from "./auth.port";

export const authHttpAdapter: AuthPort = {
  async login(username, password) {
    const { data } = await httpClient.post<TokenResponse>("/auth/login", { username, password });
    return data;
  },
  async refresh(refreshToken) {
    const { data } = await httpClient.post<TokenResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return data;
  },
  async logout(refreshToken) {
    await httpClient.post("/auth/logout", { refresh_token: refreshToken });
  },
  async me() {
    const { data } = await httpClient.get<Usuario>("/auth/me");
    return data;
  },
  async cambiarPassword(passwordActual, passwordNueva) {
    await httpClient.patch("/auth/password", {
      password_actual: passwordActual,
      password_nueva: passwordNueva,
    });
  },
};
