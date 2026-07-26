// Hook: listar/crear/editar categorías del catálogo.
//
// PR3a: el backend devuelve `Categoria[]` directo (sin paginar) en
// `GET /categorias`. `crear` ahora recibe `NuevaCategoria` (acepta
// descripcion opcional).
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { categoriasHttpAdapter } from "../services/categorias.http-adapter";
import type { Categoria, EdicionCategoria, NuevaCategoria } from "../types";

interface EstadoHook {
  categorias: Categoria[];
  cargando: boolean;
  error: string | null;
  recargar: () => Promise<void>;
  crear: (datos: NuevaCategoria) => Promise<Categoria>;
  editar: (id: number, datos: EdicionCategoria) => Promise<Categoria>;
}

export function useCategorias(): EstadoHook {
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setCategorias(await categoriasHttpAdapter.listar());
    } catch (e) {
      setError(mensajeDeError(e));
      // Sin categorías no se bloquea nada: el selector queda vacío.
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const crear = useCallback(
    async (datos: NuevaCategoria) => {
      const creada = await categoriasHttpAdapter.crear(datos);
      await recargar();
      return creada;
    },
    [recargar]
  );

  const editar = useCallback(
    async (id: number, datos: EdicionCategoria) => {
      const actualizada = await categoriasHttpAdapter.editar(id, datos);
      await recargar();
      return actualizada;
    },
    [recargar]
  );

  return { categorias, cargando, error, recargar, crear, editar };
}
