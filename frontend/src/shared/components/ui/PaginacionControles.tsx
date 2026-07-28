import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";
import { Select } from "./Select";

export interface Paginados {
  total: number;
  total_pages: number;
}

interface Props {
  paginados: Paginados | null;
  page: number;
  onCambiarPage: (page: number) => void;
  pageSize: number;
  onCambiarPageSize: (size: number) => void;
  etiqueta?: string;
}

const OPCIONES_PAGINACION = [
  { value: 10, label: "10 por pág." },
  { value: 20, label: "20 por pág." },
  { value: 25, label: "25 por pág." },
  { value: 50, label: "50 por pág." },
  { value: 100, label: "100 por pág." },
];

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
    <div className="relative z-30 flex flex-col gap-2 border-t border-zinc-100 px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
      <p className="text-xs text-zinc-500">
        {total === 0
          ? `Sin ${etiqueta}.`
          : `Mostrando ${inicio}-${fin} de ${total} ${etiqueta}.`}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-2 sm:justify-end">
        <Select
          compacto
          posicion="arriba"
          aria-label="Items por página"
          value={pageSize}
          opciones={OPCIONES_PAGINACION}
          onChange={(e) => onCambiarPageSize(Number(e.target.value))}
          className="w-28 shrink-0 sm:w-32"
        />
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <Button
            variante="secundario"
            compacto
            disabled={page <= 1}
            onClick={() => onCambiarPage(page - 1)}
            icono={<ChevronLeft className="h-4 w-4 shrink-0" aria-hidden />}
            className="!px-2 sm:!px-3"
          >
            <span className="hidden sm:inline">Anterior</span>
          </Button>
          <span className="whitespace-nowrap text-xs text-zinc-500">
            Pág. {page} / {Math.max(total_pages, 1)}
          </span>
          <Button
            variante="secundario"
            compacto
            disabled={sinMas}
            onClick={() => onCambiarPage(page + 1)}
            className="!px-2 sm:!px-3"
          >
            <span className="hidden sm:inline">Siguiente</span>
            <ChevronRight className="h-4 w-4 shrink-0" aria-hidden />
          </Button>
        </div>
      </div>
    </div>
  );
}
