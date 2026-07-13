// Hook: listar/crear categorías del catálogo.
import { useCallback, useEffect, useState } from "react";
import { categoriasHttpAdapter } from "../services/categorias.http-adapter";
import type { Categoria } from "../types";

export function useCategorias() {
  const [categorias, setCategorias] = useState<Categoria[]>([]);

  const recargar = useCallback(async () => {
    try {
      setCategorias(await categoriasHttpAdapter.listar());
    } catch {
      // Sin categorías no se bloquea nada: el selector queda vacío.
    }
  }, []);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const crear = useCallback(
    async (nombre: string) => {
      await categoriasHttpAdapter.crear(nombre);
      await recargar();
    },
    [recargar]
  );

  return { categorias, crear };
}
