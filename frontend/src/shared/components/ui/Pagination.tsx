// Paginación genérica: botones Anterior/Siguiente + números de página.
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";

interface Props {
  /** Página actual (1-based). */
  actual: number;
  /** Total de páginas. */
  total: number;
  onChange: (pagina: number) => void;
}

export function Pagination({ actual, total, onChange }: Props) {
  if (total <= 1) return null;

  const anterior = () => onChange(Math.max(1, actual - 1));
  const siguiente = () => onChange(Math.min(total, actual + 1));

  // Generar números de página a mostrar (máx 5 botones numéricos)
  const paginas: (number | "...")[] = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) paginas.push(i);
  } else {
    paginas.push(1);
    if (actual > 3) paginas.push("...");
    const inicio = Math.max(2, actual - 1);
    const fin = Math.min(total - 1, actual + 1);
    for (let i = inicio; i <= fin; i++) paginas.push(i);
    if (actual < total - 2) paginas.push("...");
    paginas.push(total);
  }

  return (
    <div className="flex items-center justify-center gap-1 px-4 py-3">
      <Button
        variante="secundario"
        compacto
        onClick={anterior}
        disabled={actual === 1}
        icono={<ChevronLeft className="h-4 w-4" />}
      >
        Anterior
      </Button>

      {paginas.map((p, i) =>
        p === "..." ? (
          <span key={`dots-${i}`} className="px-2 text-zinc-400">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={`min-w-[32px] rounded-lg px-2 py-1.5 text-sm font-medium transition-colors ${
              p === actual
                ? "bg-zinc-900 text-white"
                : "text-zinc-600 hover:bg-zinc-100"
            }`}
          >
            {p}
          </button>
        )
      )}

      <Button
        variante="secundario"
        compacto
        onClick={siguiente}
        disabled={actual === total}
        icono={<ChevronRight className="h-4 w-4" />}
      >
        Siguiente
      </Button>
    </div>
  );
}
