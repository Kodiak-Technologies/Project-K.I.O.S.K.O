// Controles de paginación: cuántas filas ver, prev/next y "mostrando X-Y de Z".
//
// Vive en `shared` porque lo usan las tablas de los tres módulos (inventario,
// ventas y documentos): toda lista larga del sistema se navega igual.
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";
import { Select } from "./Field";

/** Lo mínimo que necesita el control de cualquier respuesta paginada. */
export interface Paginados {
  total: number;
  total_pages: number;
}

interface Props {
  /** Respuesta paginada del backend. Si es `null`, no renderiza nada. */
  paginados: Paginados | null;
  /** Página actual (1-based). */
  page: number;
  onCambiarPage: (page: number) => void;
  /** Items por página. */
  pageSize: number;
  onCambiarPageSize: (size: number) => void;
  /** Etiqueta del recurso para el "Mostrando X-Y de Z". Default "ítems". */
  etiqueta?: string;
}

export function PaginacionControles({
  paginados,
  page,
  onCambiarPage,
  pageSize,
  onCambiarPageSize,
  etiqueta = "ítems",
}: Props) {
  if (!paginados) return null;
  const { total, total_pages } = paginados;
  const inicio = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const fin = Math.min(page * pageSize, total);
  const sinMas = page >= total_pages;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 px-3 py-3 sm:px-5">
      <p className="text-xs text-zinc-500">
        {total === 0
          ? `Sin ${etiqueta}.`
          : `Mostrando ${inicio}-${fin} de ${total} ${etiqueta}.`}
      </p>
      <div className="flex items-center gap-2">
        <Select
          aria-label="Items por página"
          value={pageSize}
          onChange={(e) => onCambiarPageSize(Number(e.target.value))}
          className="!min-h-0 py-1.5 text-xs"
        >
          {[10, 20, 50, 100].map((n) => (
            <option key={n} value={n}>
              {n} por pág.
            </option>
          ))}
        </Select>
        <Button
          variante="secundario"
          compacto
          disabled={page <= 1}
          onClick={() => onCambiarPage(page - 1)}
          icono={<ChevronLeft className="h-4 w-4" aria-hidden />}
        >
          Anterior
        </Button>
        <span className="text-xs text-zinc-500">
          Pág. {page} / {Math.max(total_pages, 1)}
        </span>
        <Button
          variante="secundario"
          compacto
          disabled={sinMas}
          onClick={() => onCambiarPage(page + 1)}
        >
          Siguiente
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
