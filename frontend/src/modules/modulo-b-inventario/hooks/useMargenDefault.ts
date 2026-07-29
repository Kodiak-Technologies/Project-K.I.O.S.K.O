// Margen de ganancia por defecto del negocio, para previsualizar el precio de
// venta de un producto que se da de alta desde un ingreso.
//
// Sale de `GET /configuracion`, que cualquier usuario autenticado puede leer
// (el cajero también lo necesita: es él quien carga la boleta).
import { useEffect, useState } from "react";
import { configuracionHttpAdapter } from "../../modulo-a-seguridad/services/configuracion.http-adapter";

/** Fallback si la configuración no cargó: mismo default que la BD. */
export const MARGEN_FALLBACK = 20;

export function useMargenDefault(): number {
  const [margen, setMargen] = useState(MARGEN_FALLBACK);

  useEffect(() => {
    let vigente = true;
    configuracionHttpAdapter
      .obtener()
      .then((c) => {
        // Si el backend todavía no expone el campo, no pisar el fallback.
        if (vigente && typeof c.margen_ganancia_default === "number") {
          setMargen(c.margen_ganancia_default);
        }
      })
      .catch(() => {
        // Sin configuración no se bloquea la carga del ingreso: el precio real
        // lo calcula el backend al aprobar, esto es solo la previsualización.
      });
    return () => {
      vigente = false;
    };
  }, []);

  return margen;
}
