import { Children, useEffect, useRef, useState, type ReactNode } from "react";
import { Check, ChevronDown } from "lucide-react";

export interface OpcionSelect {
  value: string | number;
  label: string;
  disabled?: boolean;
}

interface Props {
  label?: string;
  value?: string | number;
  onChange?: (e: { target: { value: string } }) => void;
  onSelectValue?: (value: string | number) => void;
  opciones?: OpcionSelect[];
  children?: ReactNode;
  placeholder?: string;
  disabled?: boolean;
  compacto?: boolean;
  error?: string | null;
  requerido?: boolean;
  className?: string;
  posicion?: "arriba" | "abajo";
  buscable?: boolean;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  "aria-label"?: string;
}

function aplanarOpciones(hijos: ReactNode): OpcionSelect[] {
  const lista: OpcionSelect[] = [];
  Children.toArray(hijos).forEach((hijo: any) => {
    if (!hijo) return;
    if (Array.isArray(hijo)) {
      lista.push(...aplanarOpciones(hijo));
    } else if (hijo.props) {
      if (hijo.props.children && Array.isArray(hijo.props.children) && hijo.type !== "option") {
        lista.push(...aplanarOpciones(hijo.props.children));
      } else {
        const val = hijo.props.value !== undefined ? hijo.props.value : hijo.props.children;
        let lbl = "";
        if (typeof hijo.props.children === "string" || typeof hijo.props.children === "number") {
          lbl = String(hijo.props.children);
        } else if (Array.isArray(hijo.props.children)) {
          lbl = hijo.props.children
            .map((item: any) => (typeof item === "object" ? "" : String(item)))
            .join("");
        } else {
          lbl = String(val ?? "");
        }
        lista.push({
          value: val,
          label: lbl || String(val ?? ""),
          disabled: Boolean(hijo.props.disabled),
        });
      }
    }
  });
  return lista;
}

export function Select({
  label,
  value,
  onChange,
  onSelectValue,
  opciones: opcionesProp,
  children,
  placeholder = "Seleccionar…",
  disabled = false,
  compacto = false,
  error,
  requerido,
  className = "",
  posicion = "abajo",
  buscable = false,
  onKeyDown,
  "aria-label": ariaLabel,
}: Props) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputBusquedaRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function manejarClicAfuera(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", manejarClicAfuera);
    return () => document.removeEventListener("mousedown", manejarClicAfuera);
  }, []);

  useEffect(() => {
    if (abierto && buscable && inputBusquedaRef.current) {
      inputBusquedaRef.current.focus();
    }
    if (!abierto) {
      setBusqueda("");
    }
  }, [abierto, buscable]);

  let listaOpciones: OpcionSelect[] = [];
  if (opcionesProp && opcionesProp.length > 0) {
    listaOpciones = opcionesProp;
  } else if (children) {
    listaOpciones = aplanarOpciones(children);
  }

  const opcionesFiltradas = buscable && busqueda.trim() !== ""
    ? listaOpciones.filter((o) => o.label.toLowerCase().includes(busqueda.toLowerCase()))
    : listaOpciones;

  const tieneValorDefinido = value !== undefined && value !== null;
  const opcionSeleccionada = tieneValorDefinido
    ? listaOpciones.find((o) => String(o.value) === String(value))
    : listaOpciones.length > 0
    ? listaOpciones[0]
    : undefined;

  let textoMostrado = placeholder;
  if (opcionSeleccionada) {
    textoMostrado = opcionSeleccionada.label;
  } else if (tieneValorDefinido && value !== "") {
    textoMostrado = typeof value === "number" || !isNaN(Number(value)) ? `${value} por pág.` : String(value);
  }

  const esPlaceholder = !opcionSeleccionada && !tieneValorDefinido;

  function seleccionar(val: string | number) {
    const strVal = String(val);
    if (onChange) {
      onChange({ target: { value: strVal } });
    }
    if (onSelectValue) {
      onSelectValue(val);
    }
    setAbierto(false);
  }

  return (
    <div ref={containerRef} className={`relative block min-w-0 ${className.includes("w-") ? "" : "w-full"} ${className}`}>
      {label && (
        <label className="mb-1 block text-sm font-medium text-zinc-700">
          {label}
          {requerido && <span className="text-peligro"> *</span>}
        </label>
      )}

      <div
        tabIndex={disabled ? -1 : 0}
        role="button"
        aria-label={ariaLabel || label || placeholder}
        aria-expanded={abierto}
        onClick={() => !disabled && setAbierto(!abierto)}
        onKeyDown={(e) => {
          if (onKeyDown) onKeyDown(e);
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            setAbierto(!abierto);
          }
        }}
        className={`flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg border bg-white text-zinc-900 shadow-sm transition-all ${
          compacto ? "px-2.5 py-1.5 text-xs sm:text-sm" : "min-h-tactil px-3 py-2 text-sm"
        } ${
          disabled
            ? "cursor-not-allowed border-zinc-200 bg-zinc-100 text-zinc-400"
            : error
            ? "border-peligro ring-1 ring-peligro"
            : "border-zinc-300 hover:border-zinc-400 focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
        } ${abierto ? "border-zinc-500 ring-1 ring-zinc-500" : ""}`}
      >
        <span className={`truncate ${esPlaceholder ? "text-zinc-400" : "font-medium text-zinc-800"}`}>
          {textoMostrado}
        </span>
        <ChevronDown
          style={{ color: "var(--color-secundario)" }}
          className={`h-4 w-4 shrink-0 transition-transform duration-200 ${abierto ? "rotate-180" : ""}`}
        />
      </div>

      {abierto && !disabled && (
        <div
          className={`animate-in fade-in-50 zoom-in-95 absolute left-0 z-50 max-h-60 w-full overflow-auto rounded-xl border border-zinc-200 bg-white py-1 shadow-lg ring-1 ring-black/5 ${
            posicion === "arriba" ? "bottom-full mb-1" : "top-full mt-1"
          }`}
        >
          {buscable && (
            <div className="sticky top-0 z-10 border-b border-zinc-100 bg-white p-1.5">
              <input
                ref={inputBusquedaRef}
                type="text"
                className="w-full rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
                placeholder="Buscar…"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                onKeyDown={(e) => e.stopPropagation()}
              />
            </div>
          )}
          {opcionesFiltradas.length === 0 ? (
            <div className="px-3 py-2 text-xs text-zinc-400">No se encontraron opciones</div>
          ) : (
            opcionesFiltradas.map((opcion) => {
              const estaSeleccionado = opcionSeleccionada
                ? String(opcion.value) === String(opcionSeleccionada.value)
                : String(opcion.value) === String(value);
              return (
                <button
                  key={String(opcion.value)}
                  type="button"
                  disabled={opcion.disabled}
                  onClick={() => !opcion.disabled && seleccionar(opcion.value)}
                  className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors ${
                    opcion.disabled
                      ? "cursor-not-allowed text-zinc-300"
                      : estaSeleccionado
                      ? "bg-zinc-100 font-medium text-zinc-900"
                      : "text-zinc-700 hover:bg-zinc-50 hover:text-zinc-900"
                  }`}
                >
                  <span className="truncate">{opcion.label}</span>
                  {estaSeleccionado && (
                    <Check style={{ color: "var(--color-secundario)" }} className="ml-2 h-4 w-4 shrink-0" />
                  )}
                </button>
              );
            })
          )}
        </div>
      )}

      {error && <p className="mt-1 text-xs text-peligro">{error}</p>}
    </div>
  );
}
