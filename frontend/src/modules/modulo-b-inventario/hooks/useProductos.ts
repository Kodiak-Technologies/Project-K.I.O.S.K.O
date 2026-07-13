// Hook: listar/crear/actualizar productos.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError, servicioNoDisponible } from "../../../shared/lib/http-client";
import { productosHttpAdapter } from "../services/productos.http-adapter";
import type { NuevoProducto, Producto } from "../types";

export function useProductos() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDisponible, setNoDisponible] = useState(false);

  const recargar = useCallback(async (busqueda?: string) => {
    setCargando(true);
    setError(null);
    try {
      setProductos(await productosHttpAdapter.listar(busqueda));
    } catch (e) {
      if (servicioNoDisponible(e)) setNoDisponible(true);
      else setError(mensajeDeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const crear = useCallback(
    async (datos: NuevoProducto) => {
      await productosHttpAdapter.crear(datos);
      await recargar();
    },
    [recargar]
  );

  const actualizar = useCallback(
    async (id: number, datos: Partial<NuevoProducto> & { activo?: boolean }) => {
      await productosHttpAdapter.actualizar(id, datos);
      await recargar();
    },
    [recargar]
  );

  return { productos, cargando, error, noDisponible, recargar, crear, actualizar };
}
