import { useState, useMemo } from "react";
import { Check, ChevronDown, Folder, Search } from "lucide-react";
import { Modal } from "./Modal";
import { Input } from "./Field";

export interface CategoriaOpcion {
  id: number;
  nombre: string;
}

interface Props {
  categorias: CategoriaOpcion[];
  valor: number | "";
  onSeleccionar: (id: number | "") => void;
  disabled?: boolean;
  className?: string;
  placeholderSinCategoria?: string;
  onKeyDown?: (e: React.KeyboardEvent) => void;
}

export function SelectorCategoriaModal({
  categorias,
  valor,
  onSeleccionar,
  disabled = false,
  className = "",
  placeholderSinCategoria = "Sin categoría",
  onKeyDown,
}: Props) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");

  const categoriaActual = useMemo(() => {
    if (valor === "" || valor === null || valor === undefined) return null;
    return categorias.find((c) => c.id === Number(valor)) ?? null;
  }, [categorias, valor]);

  const categoriasFiltradas = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return categorias;
    return categorias.filter((c) => c.nombre.toLowerCase().includes(q));
  }, [categorias, busqueda]);

  const textoBoton = categoriaActual ? categoriaActual.nombre : placeholderSinCategoria;

  function seleccionar(id: number | "") {
    onSeleccionar(id);
    setAbierto(false);
    setBusqueda("");
  }

  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setAbierto(true)}
        onKeyDown={onKeyDown}
        className={`flex items-center justify-between gap-1.5 rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs transition-colors hover:border-zinc-300 focus:outline-none focus:ring-2 focus:ring-marca disabled:opacity-50 ${className}`}
        style={{
          background: "var(--ui-fondo-panel)",
          borderColor: "var(--ui-borde)",
          color: "var(--ui-texto-principal)",
        }}
        title={textoBoton}
      >
        <span className="truncate text-left font-medium">{textoBoton}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-60" />
      </button>

      <Modal
        abierto={abierto}
        titulo="Seleccionar categoría"
        alCerrar={() => {
          setAbierto(false);
          setBusqueda("");
        }}
      >
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400 pointer-events-none" />
            <Input
              placeholder="Buscar categoría por nombre..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              autoFocus
              className="pl-9"
            />
          </div>

          <div className="max-h-[60vh] overflow-y-auto space-y-1.5 pr-1">
            {/* Opción Sin Categoría */}
            <button
              type="button"
              onClick={() => seleccionar("")}
              className="flex w-full items-center justify-between gap-3 rounded-xl p-3 text-left text-sm transition-colors"
              style={{
                border: valor === "" ? "2px solid var(--color-primario)" : "1px solid var(--ui-borde)",
                background: valor === "" ? "var(--ui-activo-bg)" : "var(--ui-fondo-panel)",
                color: "var(--ui-texto-principal)",
                fontWeight: valor === "" ? 600 : 400,
              }}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Folder className="h-4 w-4 shrink-0 opacity-50" />
                <span className="italic opacity-80">{placeholderSinCategoria}</span>
              </div>
              {valor === "" && <Check className="h-4 w-4 shrink-0 text-marca" />}
            </button>

            {/* Lista de categorías */}
            {categoriasFiltradas.length > 0 ? (
              categoriasFiltradas.map((c) => {
                const esSeleccionado = Number(valor) === c.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => seleccionar(c.id)}
                    className="flex w-full items-center justify-between gap-3 rounded-xl p-3 text-left text-sm transition-colors"
                    style={{
                      border: esSeleccionado ? "2px solid var(--color-primario)" : "1px solid var(--ui-borde)",
                      background: esSeleccionado ? "var(--ui-activo-bg)" : "var(--ui-fondo-panel)",
                      color: "var(--ui-texto-principal)",
                      fontWeight: esSeleccionado ? 600 : 400,
                    }}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <Folder className="h-4 w-4 shrink-0 text-zinc-400" />
                      <span className="break-words font-medium">{c.nombre}</span>
                    </div>
                    {esSeleccionado && <Check className="h-4 w-4 shrink-0 text-marca" />}
                  </button>
                );
              })
            ) : (
              <div className="py-8 text-center text-sm text-zinc-500">
                No se encontraron categorías que coincidan con &quot;{busqueda}&quot;
              </div>
            )}
          </div>
        </div>
      </Modal>
    </>
  );
}
