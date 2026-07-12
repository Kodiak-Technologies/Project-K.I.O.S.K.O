// Hook: consulta paginada de la bitácora con filtros.
import { useCallback, useEffect, useState } from "react";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { bitacoraHttpAdapter } from "../services/bitacora.http-adapter";
import type { BitacoraPaginada, FiltrosBitacora } from "../types";

export function useBitacora(filtrosIniciales: FiltrosBitacora = {}) {
  const [filtros, setFiltros] = useState<FiltrosBitacora>({ pagina: 1, tamano_pagina: 25, ...filtrosIniciales });
  const [datos, setDatos] = useState<BitacoraPaginada | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    setError(null);
    bitacoraHttpAdapter
      .consultar(filtros)
      .then((r) => !cancelado && setDatos(r))
      .catch((e) => !cancelado && setError(mensajeDeError(e)))
      .finally(() => !cancelado && setCargando(false));
    return () => {
      cancelado = true;
    };
  }, [filtros]);

  const aplicarFiltros = useCallback((nuevos: Partial<FiltrosBitacora>) => {
    // Cambiar un filtro siempre vuelve a la página 1 (salvo que se pida una página explícita).
    setFiltros((actuales) => ({ ...actuales, pagina: 1, ...nuevos }));
  }, []);

  return { datos, filtros, cargando, error, aplicarFiltros };
}
