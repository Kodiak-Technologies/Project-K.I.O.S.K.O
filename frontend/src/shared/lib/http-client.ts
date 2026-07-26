// Instancia única de axios. Adjunta el access token a cada request y, si el
// backend responde 401, intenta renovar la sesión con el refresh token (una vez)
// y reintenta — así la dueña no tiene que volver a loguearse en su celular.
import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL } from "../config/env";

const CLAVE_ACCESS = "kiosko_access_token";
const CLAVE_REFRESH = "kiosko_refresh_token";

export const tokenStorage = {
  obtenerAccess: () => localStorage.getItem(CLAVE_ACCESS),
  obtenerRefresh: () => localStorage.getItem(CLAVE_REFRESH),
  guardar(access: string, refresh: string) {
    localStorage.setItem(CLAVE_ACCESS, access);
    localStorage.setItem(CLAVE_REFRESH, refresh);
  },
  limpiar() {
    localStorage.removeItem(CLAVE_ACCESS);
    localStorage.removeItem(CLAVE_REFRESH);
  },
};

export const httpClient = axios.create({ baseURL: API_BASE_URL });

httpClient.interceptors.request.use((config) => {
  const token = tokenStorage.obtenerAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Callback que el AuthProvider registra para reaccionar a una sesión irrecuperable.
let alExpirarSesion: (() => void) | null = null;
export function registrarLogoutForzado(callback: () => void) {
  alExpirarSesion = callback;
}

let renovacionEnCurso: Promise<string> | null = null;

async function renovarTokens(): Promise<string> {
  const refresh = tokenStorage.obtenerRefresh();
  if (!refresh) throw new Error("Sin refresh token");
  // axios "crudo" (no httpClient) para no entrar en bucle de interceptores.
  const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refresh });
  tokenStorage.guardar(data.access_token, data.refresh_token);
  return data.access_token as string;
}

httpClient.interceptors.response.use(
  (respuesta) => respuesta,
  async (error: AxiosError) => {
    const config = error.config as (InternalAxiosRequestConfig & { _reintentado?: boolean }) | undefined;
    const es401 = error.response?.status === 401;
    const esLogin = config?.url?.includes("/auth/login");

    if (es401 && config && !config._reintentado && !esLogin && tokenStorage.obtenerRefresh()) {
      config._reintentado = true;
      try {
        renovacionEnCurso = renovacionEnCurso ?? renovarTokens();
        const nuevoAccess = await renovacionEnCurso;
        renovacionEnCurso = null;
        config.headers.Authorization = `Bearer ${nuevoAccess}`;
        return httpClient(config);
      } catch {
        renovacionEnCurso = null;
        tokenStorage.limpiar();
        alExpirarSesion?.();
      }
    }
    return Promise.reject(error);
  }
);

/** True si el endpoint aún no existe (módulo cuyo backend no está desplegado). */
export function servicioNoDisponible(error: unknown): boolean {
  return axios.isAxiosError(error) && (!error.response || [404, 501, 503].includes(error.response.status));
}

/** Extrae el mensaje de error legible que envía el backend (campo `detail`). */
export function mensajeDeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown })?.detail;
    if (typeof detail === "string") return detail;
  }
  return "Ocurrió un error inesperado. Intenta de nuevo.";
}

/**
 * sdd/modulo-b-aprobaciones-detalle-editar: extrae el `code` estructurado
 * que el backend ahora adjunta a sus respuestas de error
 * (NFR-5: `{ "detail": "...", "code": "..." }`).
 * Devuelve `undefined` si el error no tiene `code` (backward compat).
 */
export function codigoDeError(error: unknown): string | undefined {
  if (axios.isAxiosError(error)) {
    const code = (error.response?.data as { code?: unknown })?.code;
    if (typeof code === "string") return code;
  }
  return undefined;
}
