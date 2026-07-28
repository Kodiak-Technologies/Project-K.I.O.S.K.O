// Hook: consulta paginada de la bitácora con filtros.
//
// Pagina por CURSOR, no por OFFSET: la bitácora recibe eventos todo el tiempo
// (cada login, venta y ajuste escribe una fila), así que con OFFSET las filas se
// corrían entre un request y el siguiente y al pasar de página aparecían
// registros repetidos —o se salteaban—. El cursor apunta a una fila concreta,
// así que "lo que sigue" no depende de lo que se insertó arriba mientras tanto.
//
// La pila de cursores vive acá adentro: la página sigue llamando
// `aplicarFiltros({ pagina: n ± 1 })` igual que antes.
import { useCallback, useEffect, useRef, useState } from "react";
import { mensajeDeError } from "../../../shared/lib/http-client";
import { bitacoraHttpAdapter } from "../services/bitacora.http-adapter";
import type { BitacoraPaginada, FiltrosBitacora } from "../types";

export function useBitacora(filtrosIniciales: FiltrosBitacora = {}) {
  const [filtros, setFiltros] = useState<FiltrosBitacora>({ pagina: 1, tamano_pagina: 25, ...filtrosIniciales });
  const [datos, setDatos] = useState<BitacoraPaginada | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // cursores[n] = cursor con el que se pide la página n. Se llena al avanzar,
  // así "Anterior" ya lo tiene sin recalcular nada.
  const cursores = useRef<Record<number, string>>({});

  useEffect(() => {
    let cancelado = false;
    // Sin setCargando(true) acá: el spinner es solo para la primera carga. Al
    // filtrar o paginar, la tabla anterior queda visible hasta que llega la nueva.
    setError(null);
    const pagina = filtros.pagina ?? 1;
    const cursor = pagina > 1 ? cursores.current[pagina] : undefined;
    // Con cursor no se manda `pagina`: el backend la ignora de todos modos.
    const { pagina: _sinUsar, ...resto } = filtros;
    const consulta: FiltrosBitacora = cursor ? { ...resto, cursor } : filtros;
    bitacoraHttpAdapter
      .consultar(consulta)
      .then((r) => {
        if (cancelado) return;
        if (r.siguiente_cursor) cursores.current[pagina + 1] = r.siguiente_cursor;
        setDatos(r);
      })
      .catch((e) => !cancelado && setError(mensajeDeError(e)))
      .finally(() => !cancelado && setCargando(false));
    return () => {
      cancelado = true;
    };
  }, [filtros]);

  const aplicarFiltros = useCallback((nuevos: Partial<FiltrosBitacora>) => {
    // Cambiar un filtro siempre vuelve a la página 1 (salvo que se pida una página explícita).
    // Y si cambió el filtro, el resultado es otro: los cursores dejan de valer.
    if (nuevos.pagina === undefined) cursores.current = {};
    setFiltros((actuales) => ({ ...actuales, pagina: 1, ...nuevos }));
  }, []);

  return { datos, filtros, cargando, error, aplicarFiltros };
}
