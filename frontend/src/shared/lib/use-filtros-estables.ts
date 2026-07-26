// Estabiliza el objeto de filtros que recibe un hook de listado.
//
// Los componentes llaman a los hooks con un literal:
//     const { productos } = useProductos({ page_size: 100 });
// Ese objeto es NUEVO en cada render, así que usarlo como dependencia de un
// `useEffect` que hace `setState` genera un bucle infinito de requests
// (efecto -> fetch -> setState -> render -> objeto nuevo -> efecto...).
//
// Este helper devuelve una CLAVE estable por contenido (para las dependencias)
// y una ref con el último valor (para leerlo dentro del efecto sin depender
// de su identidad).
import { useRef } from "react";

export function useFiltrosEstables<T>(filtros: T | undefined) {
  const clave = JSON.stringify(filtros ?? {});
  const ref = useRef(filtros);
  ref.current = filtros;
  return { clave, ref };
}
