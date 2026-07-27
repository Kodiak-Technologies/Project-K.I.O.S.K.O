import type { ReactNode } from "react";

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
  contenedorClassName?: string;
  minAncho?: string;
}

export function Table<T>({
  columnas,
  filas,
  claveDe,
  vacio,
  alHacerClicFila,
  contenedorClassName = "max-h-[calc(100vh-16rem)]",
  minAncho = "800px",
}: Props<T>) {
  if (filas.length === 0 && vacio) return <>{vacio}</>;

  const renderColgroup = () => (
    <colgroup>
      {columnas.map((c) => (
        <col
          key={c.titulo}
          style={c.ancho ? { width: c.ancho } : undefined}
          className={c.soloEscritorio ? "hidden lg:table-column" : ""}
        />
      ))}
    </colgroup>
  );

  return (
    <div className="w-full max-w-full min-w-0 overflow-x-auto">
      <div style={{ minWidth: minAncho }} className={`overflow-y-auto [scrollbar-gutter:stable] ${contenedorClassName}`}>
        <table className="w-full border-collapse table-fixed text-sm">
          {renderColgroup()}
          <thead className="sticky top-0 z-10 border-b border-zinc-200 bg-zinc-50 shadow-sm">
            <tr className="text-left text-[11px] uppercase text-zinc-500">
              {columnas.map((c) => (
                <th
                  key={c.titulo}
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
                    className={`px-2 py-2 sm:px-3 ${c.soloEscritorio ? "hidden lg:table-cell" : ""} ${
                      c.alinear === "derecha" ? "text-right" : c.alinear === "centro" ? "text-center" : "text-left"
                    }`}
                  >
                    {c.render(fila)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
