import type { ReactNode } from "react";
import { useAltoDisponible } from "../../lib/use-alto-disponible";

export interface Columna<T> {
  titulo: string;
  render: (fila: T) => ReactNode;
  soloEscritorio?: boolean;
  alinear?: "izquierda" | "centro" | "derecha";
  ancho?: string;
}

interface Props<T> {
  columnas: Columna<T>[];
  filas: T[];
  claveDe: (fila: T) => string | number;
  vacio?: ReactNode;
  alHacerClicFila?: (fila: T) => void;
  /** Clases extra para el contenedor que scrollea. */
  contenedorClassName?: string;
  minAncho?: string;
  /**
   * Desactiva la medición automática del alto. Para pantallas donde el alto ya
   * lo reparte el contenedor (el punto de venta, con su grilla acotada): medir
   * ahí daría un resultado peor, porque la otra columna se lee como desborde.
   */
  altoDelContenedor?: boolean;
  /**
   * Por defecto el contenedor redondea sus esquinas superiores para calzar con
   * la `Card` que lo envuelve: el fondo del encabezado sticky (opaco) tapaba la
   * curva de la tarjeta y la esquina se veía recta. Ponlo en `true` cuando la
   * tabla NO va pegada al borde superior de la tarjeta (debajo del encabezado
   * de la Card o de otro contenido), donde redondear dejaría un escalón raro.
   */
  sinRedondeoSuperior?: boolean;
}

/** Menos de esto y la tabla deja de ser usable: mejor que scrollee la página. */
const ALTO_MINIMO = 200;

export function Table<T>({
  columnas,
  filas,
  claveDe,
  vacio,
  alHacerClicFila,
  contenedorClassName = "",
  minAncho = "800px",
  altoDelContenedor = false,
  sinRedondeoSuperior = false,
}: Props<T>) {
  const { ref: raizRef, altoMaximo } = useAltoDisponible<HTMLDivElement>(
    ALTO_MINIMO,
    !altoDelContenedor
  );

  if (filas.length === 0 && vacio) return <>{vacio}</>;

  return (
    // Único contenedor de scroll de la tabla: horizontal y vertical juntos.
    // Antes eran dos anidados, y el de adentro heredaba `overflow-x: auto`
    // por la regla de CSS que convierte `visible` en `auto`.
    <div
      ref={raizRef}
      style={{ maxHeight: altoMaximo }}
      // `overflow-auto` ya recorta el contenido: con `rounded-t-xl` esa curva
      // corta el fondo del encabezado sticky y deja ver la esquina redondeada
      // de la Card (antes se veía recta). El pie (paginación) y el borde inferior
      // los redondea la propia Card, así que solo hace falta arriba.
      className={`w-full min-w-0 max-w-full overflow-auto ${
        sinRedondeoSuperior ? "" : "rounded-t-xl"
      } [scrollbar-gutter:stable] ${contenedorClassName}`}
    >
      <table
        style={{ minWidth: minAncho }}
        className="w-full table-fixed border-collapse text-sm"
      >
        <thead className="sticky top-0 z-10 border-b border-zinc-200 bg-zinc-50 shadow-sm">
          <tr className="text-left text-[11px] uppercase text-zinc-500">
            {columnas.map((c) => (
              <th
                key={c.titulo}
                style={c.ancho ? { width: c.ancho } : undefined}
                className={`bg-zinc-50 px-2 py-2.5 font-medium sm:px-3 ${
                  c.soloEscritorio ? "hidden lg:table-cell" : ""
                } ${c.alinear === "derecha" ? "text-right" : c.alinear === "centro" ? "text-center" : "text-left"}`}
              >
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {filas.map((fila) => (
            <tr
              key={claveDe(fila)}
              onClick={alHacerClicFila ? () => alHacerClicFila(fila) : undefined}
              onKeyDown={
                alHacerClicFila
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        alHacerClicFila(fila);
                      }
                    }
                  : undefined
              }
              tabIndex={alHacerClicFila ? 0 : undefined}
              role={alHacerClicFila ? "button" : undefined}
              className={`transition-colors hover:bg-zinc-50 ${
                alHacerClicFila ? "cursor-pointer focus:bg-zinc-100 focus:outline-none" : ""
              }`}
            >
              {columnas.map((c) => (
                <td
                  key={c.titulo}
                  // `break-words`: con table-fixed, un texto largo sin espacios
                  // (un código de barras, una URL) se desbordaba de la celda.
                  className={`break-words px-2 py-2 sm:px-3 ${
                    c.soloEscritorio ? "hidden lg:table-cell" : ""
                  } ${c.alinear === "derecha" ? "text-right" : c.alinear === "centro" ? "text-center" : "text-left"}`}
                >
                  {c.render(fila)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
