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

const MENSAJE_GENERICO = "No pudimos completar la operación. Intenta de nuevo en unos segundos.";
const MENSAJE_SIN_CONEXION =
  "No hay conexión con el sistema. Revisa el internet y vuelve a intentar.";

/**
 * Mensaje listo para mostrarle a la usuaria. Solo confiamos en el `detail` que
 * manda el backend cuando es un error "de negocio" (4xx: stock insuficiente,
 * datos inválidos…). Los 5xx y las caídas de red traen textos de diagnóstico
 * que no le sirven a nadie detrás del mostrador: se reemplazan por uno claro.
 */
export function mensajeDeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    if (!status) return MENSAJE_SIN_CONEXION;
    const detail = (error.response?.data as { detail?: unknown })?.detail;
    if (status < 500 && typeof detail === "string" && detail.trim()) return detail;
  }
  return MENSAJE_GENERICO;
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

/** Extrae el id de archivo de cualquier forma de enlace de Google Drive. */
export function fileIdDeDrive(url: string | null | undefined): string | null {
  if (!url) return null;
  if (!url.includes("drive.google.com") && !url.includes("googleusercontent.com")) {
    return null;
  }
  return (
    url.match(/[?&]id=([a-zA-Z0-9_-]+)/)?.[1] ??
    url.match(/\/d\/([a-zA-Z0-9_-]+)/)?.[1] ??
    null
  );
}

/**
 * Formas en que Google sirve un mismo archivo de Drive, en orden de preferencia.
 *
 * Ninguna es estable: Google cambia cuál responde imagen y cuál devuelve 404 o
 * la página HTML del visor, y además dependen de que el archivo sea público.
 * Por eso no elegimos una: se prueban en orden hasta que alguna cargue
 * (ver `ImagenConRespaldo`). Si la URL no es de Drive se devuelve tal cual.
 */
export function urlsDeImagen(url: string | null | undefined): string[] {
  if (!url) return [];
  const id = fileIdDeDrive(url);
  if (!id) return [url];
  return [
    `https://lh3.googleusercontent.com/d/${id}`,
    `https://drive.google.com/thumbnail?id=${id}&sz=w1000`,
    `https://drive.google.com/uc?export=view&id=${id}`,
  ];
}

/** Primera URL candidata. Para `<img>` sueltos que no reintentan. */
export function normalizarImagenUrl(url: string | null | undefined): string {
  return urlsDeImagen(url)[0] ?? "";
}

/**
 * Enlace para ABRIR el archivo, no para incrustarlo.
 *
 * Va al visor de Drive, que muestra la imagen aunque el enlace directo no
 * sirva. Es lo que corresponde en un `href`: ahí no hay reintento posible,
 * así que conviene la forma más confiable aunque no sirva para un `<img>`.
 */
export function urlParaAbrir(url: string | null | undefined): string {
  const id = fileIdDeDrive(url);
  return id ? `https://drive.google.com/file/d/${id}/view` : (url ?? "");
}
