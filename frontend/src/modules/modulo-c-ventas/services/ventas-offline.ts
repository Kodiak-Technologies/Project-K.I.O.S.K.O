// Modo de contingencia del POS (HU-C10, RF-26): si se cae el internet, las
// ventas se guardan en el navegador (localStorage) y se sincronizan solas al
// volver la conexión. Ninguna venta se pierde:
//  - cada venta local lleva un client_uuid ÚNICO → reintentar nunca duplica
//  - el catálogo y el turno se cachean para poder seguir vendiendo sin backend
//  - si el servidor rechaza una venta al sincronizar (ej. otro cajero agotó el
//    stock), queda marcada con su error para revisarla, nunca se descarta sola.
import type { Producto } from "../../modulo-b-inventario/types";
import { ventasHttpAdapter } from "./ventas.http-adapter";
import type { NuevaVenta, TurnoCaja, Venta, VentaPendiente } from "../types";

const CLAVE_PENDIENTES = "kiosko_ventas_pendientes";
const CLAVE_PRODUCTOS = "kiosko_productos_cache";
const CLAVE_TURNO = "kiosko_turno_cache";

function leer<T>(clave: string, porDefecto: T): T {
  try {
    const crudo = localStorage.getItem(clave);
    return crudo ? (JSON.parse(crudo) as T) : porDefecto;
  } catch {
    return porDefecto;
  }
}

// ---------- Cola de ventas pendientes ----------
export const colaOffline = {
  listar(): VentaPendiente[] {
    return leer<VentaPendiente[]>(CLAVE_PENDIENTES, []);
  },

  guardar(venta: NuevaVenta, extras: Omit<VentaPendiente, "uuid" | "venta" | "vendida_en">): VentaPendiente {
    const pendiente: VentaPendiente = {
      uuid: crypto.randomUUID(),
      vendida_en: new Date().toISOString(),
      venta,
      ...extras,
    };
    const cola = colaOffline.listar();
    cola.push(pendiente);
    localStorage.setItem(CLAVE_PENDIENTES, JSON.stringify(cola));
    return pendiente;
  },

  descartar(uuid: string) {
    const cola = colaOffline.listar().filter((p) => p.uuid !== uuid);
    localStorage.setItem(CLAVE_PENDIENTES, JSON.stringify(cola));
  },

  /** Envía las pendientes una por una. Devuelve cuántas entraron y los errores. */
  async sincronizar(): Promise<{ sincronizadas: Venta[]; conError: VentaPendiente[] }> {
    const sincronizadas: Venta[] = [];
    const conError: VentaPendiente[] = [];
    for (const pendiente of colaOffline.listar()) {
      try {
        const venta = await ventasHttpAdapter.registrar({
          ...pendiente.venta,
          client_uuid: pendiente.uuid,
          registrada_offline: true,
          vendida_en: pendiente.vendida_en,
        });
        sincronizadas.push(venta);
        colaOffline.descartar(pendiente.uuid);
      } catch (e: unknown) {
        const respuesta = (e as { response?: { status?: number; data?: { detail?: string } } }).response;
        if (respuesta?.status && respuesta.status >= 400 && respuesta.status < 500) {
          // El backend la rechazó (sin stock, sin turno...): se conserva marcada
          // con el motivo para que el cajero decida, NUNCA se pierde en silencio.
          pendiente.error = respuesta.data?.detail ?? "El servidor rechazó esta venta.";
          const cola = colaOffline.listar().map((p) => (p.uuid === pendiente.uuid ? pendiente : p));
          localStorage.setItem(CLAVE_PENDIENTES, JSON.stringify(cola));
          conError.push(pendiente);
        } else {
          break; // seguimos sin conexión: se reintenta en la próxima
        }
      }
    }
    return { sincronizadas, conError };
  },
};

// ---------- Cachés para operar sin backend ----------
export const cacheOffline = {
  guardarProductos(productos: Producto[]) {
    localStorage.setItem(CLAVE_PRODUCTOS, JSON.stringify(productos));
  },
  productos(): Producto[] {
    return leer<Producto[]>(CLAVE_PRODUCTOS, []);
  },
  /** Descuenta stock del caché local para no sobrevender mientras no hay internet. */
  descontarStock(items: { producto_id: number; cantidad: number }[]) {
    const productos = cacheOffline.productos().map((p) => {
      const item = items.find((i) => i.producto_id === p.id);
      return item ? { ...p, stock: Math.max(0, p.stock - item.cantidad) } : p;
    });
    cacheOffline.guardarProductos(productos);
    return productos;
  },
  guardarTurno(turno: TurnoCaja | null) {
    localStorage.setItem(CLAVE_TURNO, JSON.stringify(turno));
  },
  turno(): TurnoCaja | null {
    return leer<TurnoCaja | null>(CLAVE_TURNO, null);
  },
};
