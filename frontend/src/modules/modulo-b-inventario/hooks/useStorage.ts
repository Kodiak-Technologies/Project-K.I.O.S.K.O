// Hook: subir archivos a Storage. Maneja estado de progreso y error de red.
// Devuelve un callback `subir` que no expone `AbortController` aún (es suficiente
// para el flujo actual: foto de producto / boleta de ingreso).
import { useCallback, useState } from "react";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { storageHttpAdapter } from "../services/storage.http-adapter";
import type { StorageResult } from "../types";

interface EstadoHook {
  subiendo: boolean;
  error: string | null;
  /** Última URL firmada devuelta por el backend. */
  ultimoResultado: StorageResult | null;
  subir: (carpeta: string, archivo: File) => Promise<StorageResult | null>;
  limpiar: () => void;
}

export function useStorage(): EstadoHook {
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ultimoResultado, setUltimoResultado] = useState<StorageResult | null>(null);

  const subir = useCallback(async (carpeta: string, archivo: File) => {
    setSubiendo(true);
    setError(null);
    try {
      const resp = await storageHttpAdapter.subir(carpeta, archivo);
      setUltimoResultado(resp);
      return resp;
    } catch (e) {
      setError(mensajeDeError(e));
      return null;
    } finally {
      setSubiendo(false);
    }
  }, []);

  const limpiar = useCallback(() => {
    setError(null);
    setUltimoResultado(null);
  }, []);

  return { subiendo, error, ultimoResultado, subir, limpiar };
}
