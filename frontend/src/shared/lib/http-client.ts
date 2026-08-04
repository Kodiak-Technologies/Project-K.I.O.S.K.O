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

/**
 * Tope de espera por request. Sin esto axios espera indefinidamente: si el
 * backend se cuelga, la pantalla se queda con el spinner puesto para siempre y
 * la usuaria no tiene forma de saber si su clic entró o no.
 *
 * 30s es holgado a propósito: Cloud Run arranca en frío tras un rato sin
 * tráfico y la primera petición del día paga ese arranque. Una consulta normal
 * responde muy por debajo.
 */
export const TIMEOUT_MS = 30_000;

/**
 * Para lo que legítimamente tarda: subir una boleta o el logo a Drive, bajar un
 * respaldo o exportar un reporte. Con el tope normal, una subida desde el
 * celular con mala señal se cortaría estando sana.
 *
 * Se pasa por request: `httpClient.post(url, fd, { timeout: TIMEOUT_ARCHIVOS_MS })`.
 */
export const TIMEOUT_ARCHIVOS_MS = 120_000;

export const httpClient = axios.create({ baseURL: API_BASE_URL, timeout: TIMEOUT_MS });

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
  // Eso también lo deja fuera del timeout de la instancia, así que va explícito:
  // todo request que reciba un 401 queda esperando a `renovacionEnCurso`, y si
  // esta promesa no termina nunca, la app entera se cuelga en silencio.
  const { data } = await axios.post(
    `${API_BASE_URL}/auth/refresh`,
    { refresh_token: refresh },
    { timeout: TIMEOUT_MS }
  );
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

/** True si el request se cortó por el timeout, no por una respuesta del backend. */
export function esTimeout(error: unknown): boolean {
  return (
    axios.isAxiosError(error) &&
    !error.response &&
    (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT")
  );
}

/** True si el endpoint aún no existe (módulo cuyo backend no está desplegado).
 *
 *  Un timeout NO cuenta: el endpoint puede existir perfectamente y estar lento.
 *  Sin esta salvedad una lista que tarda de más pintaría "módulo pendiente",
 *  que es un diagnóstico falso y sin salida para la usuaria. */
export function servicioNoDisponible(error: unknown): boolean {
  if (esTimeout(error)) return false;
  return axios.isAxiosError(error) && (!error.response || [404, 501, 503].includes(error.response.status));
}

const MENSAJE_GENERICO = "No pudimos completar la operación. Intenta de nuevo en unos segundos.";
const MENSAJE_SIN_CONEXION =
  "No hay conexión con el sistema. Revisa el internet y vuelve a intentar.";
const MENSAJE_TIMEOUT =
  "El sistema está tardando demasiado en responder. Verifica si la operación quedó registrada antes de repetirla.";

/**
 * Mensaje listo para mostrarle a la usuaria. Solo confiamos en el `detail` que
 * manda el backend cuando es un error "de negocio" (4xx: stock insuficiente,
 * datos inválidos…). Los 5xx y las caídas de red traen textos de diagnóstico
 * que no le sirven a nadie detrás del mostrador: se reemplazan por uno claro.
 */
export function mensajeDeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    // Un timeout no distingue "no llegó" de "llegó y todavía está procesando":
    // por eso el texto pide verificar en vez de invitar a reintentar a ciegas.
    if (esTimeout(error)) return MENSAJE_TIMEOUT;
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
