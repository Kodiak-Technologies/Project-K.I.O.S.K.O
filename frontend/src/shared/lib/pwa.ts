// App instalable (PWA): registra el service worker, captura el aviso de
// instalación del navegador y se actualiza sola cuando se publica una versión
// nueva. Instalada, la web se abre como app (pantalla completa, con su ícono).
import { useSyncExternalStore } from "react";

type AvisoInstalacion = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export type SistemaOperativo = "ios" | "android" | "otro";

let aviso: AvisoInstalacion | null = null;
let instaladaAhora = false;
const oyentes = new Set<() => void>();

function enModoApp(): boolean {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function sistema(): SistemaOperativo {
  const ua = navigator.userAgent;
  // iPadOS se presenta como Mac: se reconoce por la pantalla táctil.
  if (/iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)) {
    return "ios";
  }
  if (/Android/.test(ua)) return "android";
  return "otro";
}

function calcular() {
  const instalada = enModoApp() || instaladaAhora;
  const so = sistema();
  return {
    /** Mostrar el botón: si el navegador instala con un toque, o en un celular (con instrucciones). */
    visible: !instalada && (aviso !== null || so !== "otro"),
    /** El navegador instala con un toque (Chrome/Edge en Android y computadora). */
    directo: aviso !== null,
    instalada,
    sistema: so,
  };
}

let estado = calcular();

function notificar() {
  estado = calcular();
  oyentes.forEach((f) => f());
}

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault(); // se usa nuestro botón en vez de la barra del navegador
  aviso = e as AvisoInstalacion;
  notificar();
});
window.addEventListener("appinstalled", () => {
  aviso = null;
  instaladaAhora = true;
  notificar();
});

// Solo en producción: en `npm run dev` un service worker cachearía el código
// que Vite recarga en caliente.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  const habiaVersion = navigator.serviceWorker.controller !== null;
  let pendiente = false;
  const registrar = () =>
    navigator.serviceWorker
      .register("/sw.js")
      .then((reg) => {
        // Al volver a la app, revisar si hay una versión más nueva (máx. cada 10 min).
        let ultima = Date.now();
        document.addEventListener("visibilitychange", () => {
          if (document.visibilityState !== "visible") return;
          if (pendiente) return window.location.reload();
          if (Date.now() - ultima > 10 * 60_000) {
            ultima = Date.now();
            reg.update().catch(() => {});
          }
        });
      })
      .catch(() => {});
  if (document.readyState === "complete") registrar();
  else window.addEventListener("load", registrar);
  // Versión nueva activa: recargar ya si la app está en segundo plano, o la
  // próxima vez que vuelva a verse (nunca en medio de una venta).
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!habiaVersion) return;
    if (document.visibilityState === "hidden") window.location.reload();
    else pendiente = true;
  });
}

/** Abre el diálogo de instalación del navegador. false si no está disponible (iOS u otros). */
export async function instalarApp(): Promise<boolean> {
  if (!aviso) return false;
  await aviso.prompt();
  const { outcome } = await aviso.userChoice;
  aviso = null;
  if (outcome === "accepted") instaladaAhora = true;
  notificar();
  return true;
}

export function useInstalarApp() {
  return useSyncExternalStore(
    (f) => {
      oyentes.add(f);
      return () => oyentes.delete(f);
    },
    () => estado
  );
}
