// Modal accesible: cierra con Escape o clic en el fondo, bloquea el scroll del body.
import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface Props {
  abierto: boolean;
  titulo: string;
  alCerrar: () => void;
  /** Botones del pie (normalmente Cancelar + acción principal). */
  pie?: ReactNode;
  children: ReactNode;
}

export function Modal({ abierto, titulo, alCerrar, pie, children }: Props) {
  useEffect(() => {
    if (!abierto) return;
    const manejarTecla = (e: KeyboardEvent) => e.key === "Escape" && alCerrar();
    document.addEventListener("keydown", manejarTecla);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", manejarTecla);
      document.body.style.overflow = "";
    };
  }, [abierto, alCerrar]);

  if (!abierto) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-zinc-900/40 p-0 sm:items-center sm:p-4"
      onClick={alCerrar}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className="max-h-[90vh] w-full overflow-y-auto rounded-t-2xl bg-white shadow-lg sm:max-w-lg sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
          <h3 className="font-semibold text-zinc-900">{titulo}</h3>
          <button
            onClick={alCerrar}
            aria-label="Cerrar"
            className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
          >
            <X className="h-5 w-5" />
          </button>
        </header>
        <div className="px-5 py-4">{children}</div>
        {pie && <footer className="flex justify-end gap-2 border-t border-zinc-100 px-5 py-4">{pie}</footer>}
      </div>
    </div>,
    document.body
  );
}
