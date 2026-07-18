// Tabla genérica del sistema: contenedor con scroll horizontal propio (la página
// nunca scrollea de lado), cabecera gris y filas con hover. Columnas por render prop.
import type { ReactNode } from "react";

export interface Columna<T> {
  titulo: string;
  render: (fila: T) => ReactNode;
  /** Ocultar en pantallas angostas (tablet vertical / móvil). */
  soloEscritorio?: boolean;
  alinear?: "izquierda" | "centro" | "derecha";
}

interface Props<T> {
  columnas: Columna<T>[];
  filas: T[];
  claveDe: (fila: T) => string | number;
  /** Qué mostrar cuando no hay filas (normalmente un <EmptyState/>). */
  vacio?: ReactNode;
}

export function Table<T>({ columnas, filas, claveDe, vacio }: Props<T>) {
  if (filas.length === 0 && vacio) return <>{vacio}</>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 text-left text-[11px] uppercase text-zinc-500">
            {columnas.map((c) => (
              <th
                key={c.titulo}
                className={`px-2 py-2 font-medium sm:px-3 ${c.soloEscritorio ? "hidden lg:table-cell" : ""} ${
                  c.alinear === "derecha" ? "text-right" : c.alinear === "centro" ? "text-center" : ""
                }`}
              >
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={claveDe(fila)} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50">
              {columnas.map((c) => (
                <td
                  key={c.titulo}
                  className={`px-2 py-2 sm:px-3 ${c.soloEscritorio ? "hidden lg:table-cell" : ""} ${
                    c.alinear === "derecha" ? "text-right" : c.alinear === "centro" ? "text-center" : ""
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
  );
}
