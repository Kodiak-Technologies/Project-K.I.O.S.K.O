import { useEffect, useRef, useState } from "react";
import { Pipette } from "lucide-react";

export interface ColorPickerProps {
  label?: string;
  descripcion?: string;
  value: string;
  onChange: (hex: string) => void;
  presets?: string[];
  className?: string;
}

const PRESETS_DEFECTO = [
  "#ef4444", "#f97316", "#f59e0b", "#eab308",
  "#84cc16", "#22c55e", "#10b981", "#14b8a6",
  "#06b6d4", "#0ea5e9", "#3b82f6", "#6366f1",
  "#8b5cf6", "#a855f7", "#ec4899", "#f43f5e",
  "#0f172a", "#334155", "#64748b", "#94a3b8",
  "#78350f", "#b45309", "#047857", "#1d4ed8",
];

function esHexValido(v: string) {
  return /^#[0-9a-fA-F]{6}$/.test(v);
}

export function ColorPicker({
  label,
  descripcion,
  value,
  onChange,
  presets = PRESETS_DEFECTO,
  className = "",
}: ColorPickerProps) {
  const [abierto, setAbierto] = useState(false);
  const [posicion, setPosicion] = useState<"abajo" | "arriba">("abajo");
  const [texto, setTexto] = useState(value);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTexto(value);
  }, [value]);

  useEffect(() => {
    function fuera(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setAbierto(false);
    }
    function tecla(e: KeyboardEvent) {
      if (e.key === "Escape") setAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fuera);
      document.removeEventListener("keydown", tecla);
    };
  }, []);

  function alternar() {
    if (!abierto && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setPosicion(window.innerHeight - rect.bottom < 340 && rect.top > 300 ? "arriba" : "abajo");
    }
    setAbierto((a) => !a);
  }

  function alEscribir(v: string) {
    const limpio = ("#" + v.replace(/[^0-9a-fA-F]/g, "")).slice(0, 7);
    setTexto(limpio);
    if (esHexValido(limpio)) onChange(limpio.toLowerCase());
  }

  const seleccionado = value.toLowerCase();
  const valorNativo = esHexValido(texto) ? texto : esHexValido(value) ? value : "#000000";

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="flex items-center justify-between gap-3 rounded-lg border border-zinc-300 bg-white px-3 py-2.5 shadow-sm">
        <div className="min-w-0">
          {label && <span className="block text-sm font-medium text-zinc-700">{label}</span>}
          {descripcion ? (
            <span className="block truncate text-xs text-zinc-400">{descripcion}</span>
          ) : (
            <span className="block font-mono text-xs uppercase tracking-wide text-zinc-400">{seleccionado}</span>
          )}
        </div>
        <button
          type="button"
          onClick={alternar}
          aria-label={label ? `Elegir ${label}` : "Elegir color"}
          aria-expanded={abierto}
          className={`relative h-9 w-9 shrink-0 rounded-full border-2 border-white shadow-md transition-transform hover:scale-105 ${
            abierto ? "ring-2 ring-zinc-500" : "ring-1 ring-black/10"
          }`}
          style={{ backgroundColor: value }}
        />
      </div>

      {abierto && (
        <div
          className={`animate-in fade-in zoom-in-95 absolute right-0 z-[100] w-72 rounded-xl border border-zinc-200 bg-white p-3.5 shadow-2xl duration-100 ${
            posicion === "arriba" ? "bottom-full mb-2" : "top-full mt-2"
          }`}
        >
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-zinc-400">Colores rápidos</p>
          <div className="grid grid-cols-8 gap-2">
            {presets.map((c) => {
              const activo = c.toLowerCase() === seleccionado;
              return (
                <button
                  key={c}
                  type="button"
                  onClick={() => onChange(c.toLowerCase())}
                  aria-label={c}
                  title={c}
                  className={`h-6 w-6 rounded-full shadow-sm transition-transform hover:scale-110 ${
                    activo ? "ring-2 ring-zinc-600 ring-offset-2 ring-offset-white" : "ring-1 ring-black/10"
                  }`}
                  style={{ backgroundColor: c }}
                />
              );
            })}
          </div>

          <div className="mt-3.5 border-t border-zinc-100 pt-3">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-zinc-400">Personalizado</p>
            <div className="flex items-center gap-2.5">
              <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-full border border-zinc-200 shadow-sm ring-1 ring-black/5">
                <input
                  type="color"
                  value={valorNativo}
                  onChange={(e) => onChange(e.target.value.toLowerCase())}
                  aria-label="Selector de color personalizado"
                  className="absolute left-1/2 top-1/2 h-14 w-14 -translate-x-1/2 -translate-y-1/2 cursor-pointer border-0 bg-transparent p-0 [appearance:none]"
                />
                <span className="pointer-events-none absolute bottom-0.5 right-0.5 rounded-full bg-white/85 p-0.5 shadow-sm">
                  <Pipette className="h-3 w-3 text-zinc-600" aria-hidden />
                </span>
              </div>
              <div className="relative flex-1">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-zinc-400">
                  #
                </span>
                <input
                  value={texto.replace(/^#/, "").toUpperCase()}
                  onChange={(e) => alEscribir(e.target.value)}
                  maxLength={6}
                  spellCheck={false}
                  inputMode="text"
                  aria-label="Código hexadecimal"
                  className="w-full rounded-lg border border-zinc-300 bg-white py-2 pl-6 pr-3 text-sm font-medium uppercase tracking-widest text-zinc-800 shadow-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
