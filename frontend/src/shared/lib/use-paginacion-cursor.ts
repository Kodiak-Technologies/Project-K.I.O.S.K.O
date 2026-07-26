// Paginación por cursor (keyset) para los listados que se escriben mientras
// el usuario los navega: bitácora, movimientos de inventario e ingresos.
//
// Con `page`/`OFFSET` el backend cuenta posiciones sobre los datos del momento:
// si entra una fila mientras alguien mira la página 1, todo se corre un lugar y
// la primera fila de la página 2 es una que ya vio. El cursor apunta a una fila
// concreta ("dame lo que sigue después de esta"), así que no repite ni saltea.
//
// El control de paginación no cambia: sólo ofrece Anterior/Siguiente, y este
// hook traduce esos ±1 a avanzar o retroceder por la pila de cursores.
import { useCallback, useRef, useState } from "react";

export interface PaginacionCursor {
  /** Página actual (1-based). Sólo para mostrar; no se manda al backend. */
  page: number;
  pageSize: number;
  /** Cursor a mandar en el request. `undefined` en la primera página. */
  cursor: string | undefined;
  /** Encaja con `onCambiarPage` de `PaginacionControles` (siempre ±1). */
  onCambiarPage: (page: number) => void;
  onCambiarPageSize: (size: number) => void;
  /** Guarda el `siguiente_cursor` de la respuesta recién recibida. */
  registrarRespuesta: (siguienteCursor: string | null | undefined) => void;
  /** Vuelve a la primera página y descarta los cursores acumulados.
   *  Hay que llamarlo cuando cambian los filtros: un cursor viejo apunta a
   *  una fila que quizá ya no entra en el nuevo resultado. */
  reiniciar: () => void;
}

export function usePaginacionCursor(pageSizeInicial = 20): PaginacionCursor {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(pageSizeInicial);
  // cursores[n] = cursor con el que se pide la página n+1.
  // Se llena a medida que se avanza, así "Anterior" ya lo tiene.
  const cursores = useRef<Record<number, string>>({});

  // Espejo de `page` en una ref: `registrarRespuesta` necesita saber a qué
  // página pertenece la respuesta sin volver a crearse en cada cambio.
  const pageRef = useRef(1);
  pageRef.current = page;

  const registrarRespuesta = useCallback(
    (siguienteCursor: string | null | undefined) => {
      if (siguienteCursor) cursores.current[pageRef.current + 1] = siguienteCursor;
    },
    []
  );

  const reiniciar = useCallback(() => {
    cursores.current = {};
    setPage(1);
  }, []);

  const onCambiarPageSize = useCallback(
    (size: number) => {
      setPageSize(size);
      reiniciar(); // otro tamaño ⇒ otros cortes: los cursores no sirven
    },
    [reiniciar]
  );

  return {
    page,
    pageSize,
    cursor: page === 1 ? undefined : cursores.current[page],
    onCambiarPage: setPage,
    onCambiarPageSize,
    registrarRespuesta,
    reiniciar,
  };
}
