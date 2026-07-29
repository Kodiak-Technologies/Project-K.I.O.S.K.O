// Alto máximo para que un área larga (una tabla, una lista) termine justo en el
// borde inferior de la pantalla en vez de estirar la página.
//
// El problema que resuelve: si el contenido crece sin límite, la página queda
// más alta que el viewport y aparece una barra vertical al costado, además de
// la que ya tiene el área. Queremos siempre UNA sola barra, y que sea la del
// área que corresponde.
//
// Antes esto se hacía con `max-h-[calc(100vh - 16rem)]` a ojo, con un número
// distinto por pantalla; cuando el encabezado o los filtros no medían
// exactamente eso, el cálculo fallaba.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

/** Colchón para que un redondeo no vuelva a disparar el scroll de la página. */
const RESPIRO = 4;

/**
 * Devuelve una `ref` para el elemento que scrollea y el `maxHeight` que le
 * corresponde, o `undefined` cuando no hace falta limitarlo.
 *
 * La medición suelta el elemento un instante, lee cuánto desborda la página en
 * ese estado y le descuenta esa diferencia. No sirve intentar el camino
 * inverso —colapsar el elemento y leer el alto del resto con `scrollHeight`—
 * porque `scrollHeight` nunca devuelve menos que `clientHeight`: apenas la
 * página entra en el viewport, informa el alto del viewport y el cálculo da
 * siempre "no queda espacio".
 *
 * Como contrapartida, asume UN área medida por pantalla: con dos, cada una se
 * descontaría el desborde que provoca la otra y ninguna se limitaría. Las
 * pantallas de dos columnas (el punto de venta) reparten el alto con flex y no
 * usan este hook.
 *
 * @param altoMinimo Por debajo de esto el área deja de ser usable: se prefiere
 * no limitarla y que scrollee la página, para no terminar con dos barras.
 * @param activo En `false` no mide ni limita: para contenedores que ya reparten
 * el alto por su cuenta.
 */
export function useAltoDisponible<T extends HTMLElement>(altoMinimo: number, activo = true) {
  const ref = useRef<T>(null);
  const [altoMaximo, setAltoMaximo] = useState<number>();

  const medir = useCallback(() => {
    const el = ref.current;
    if (!el || !activo) return;
    const scroller = (el.closest("main") as HTMLElement | null) ?? document.documentElement;

    // Al soltar el límite el elemento deja de ser scrollable un instante y el
    // navegador le pone `scrollTop` en 0. Lo guardamos para restaurarlo: si no,
    // cualquier render con la tabla desplazada (p. ej. tocar el lápiz para
    // editar una fila del medio) la mandaba de vuelta al inicio.
    const scrollTopPrevio = el.scrollTop;

    // Momentáneo: se restaura antes de salir, dentro del mismo frame.
    const limiteAplicado = el.style.maxHeight;
    el.style.maxHeight = "none";
    const altoDeseado = el.scrollHeight;
    const desborde = scroller.scrollHeight - scroller.clientHeight;
    el.style.maxHeight = limiteAplicado;
    el.scrollTop = scrollTopPrevio;

    const disponible = altoDeseado - desborde - RESPIRO;
    // Sin desborde entra entera y no necesita barra propia.
    const nuevo = desborde <= 0 || disponible < altoMinimo ? undefined : disponible;

    // La medición siempre parte del elemento suelto, así que el resultado es
    // estable y React corta el re-render al repetirse: no hay bucle.
    setAltoMaximo((previo) => (previo === nuevo ? previo : nuevo));
  }, [altoMinimo, activo]);

  // Después de cada render: cubre filtros que se despliegan, avisos que
  // aparecen y cualquier cambio de alto por encima del área.
  useLayoutEffect(medir);

  useEffect(() => {
    window.addEventListener("resize", medir);
    return () => window.removeEventListener("resize", medir);
  }, [medir]);

  return { ref, altoMaximo };
}
