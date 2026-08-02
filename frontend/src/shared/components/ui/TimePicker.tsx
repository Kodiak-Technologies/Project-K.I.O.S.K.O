import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Clock, X } from "lucide-react";

export interface TimePickerProps {
  label?: string;
  value?: string;
  onChange: (value: string | undefined) => void;
  placeholder?: string;
  disabled?: boolean;
  requerido?: boolean;
  className?: string;
}

const HORAS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const MINUTOS_SUGERIDOS = ["00", "15", "30", "45"];

export function TimePicker({
  label,
  value,
  onChange,
  placeholder = "hh:mm",
  disabled = false,
  requerido = false,
  className = "",
}: TimePickerProps) {
  const [abierto, setAbierto] = useState(false);
  const [posicionEfectiva, setPosicionEfectiva] = useState<"abajo" | "arriba">("abajo");
  const [estiloPopover, setEstiloPopover] = useState<React.CSSProperties>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const [horaSel, setHoraSel] = useState(() => (value ? value.split(":")[0] : "08"));
  const [minSel, setMinSel] = useState(() => (value ? value.split(":")[1] : "00"));

  useEffect(() => {
    if (value) {
      const [h, m] = value.split(":");
      if (h) setHoraSel(h);
      if (m) setMinSel(m);
    }
  }, [value]);

  useEffect(() => {
    function alHacerClicFuera(e: MouseEvent) {
      const target = e.target as Node;
      if (
        containerRef.current &&
        !containerRef.current.contains(target) &&
        popoverRef.current &&
        !popoverRef.current.contains(target)
      ) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", alHacerClicFuera);
    return () => document.removeEventListener("mousedown", alHacerClicFuera);
  }, []);

  function recalcularPosicion() {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const topBarAlto = 64; // Altura de la barra superior (TopBar)
    const marginMinimoTop = topBarAlto + 8;
    const altoPop = 260;
    const anchoPop = 240; // w-60 = 240px
    const viewportAncho = window.innerWidth;
    const viewportAlto = window.innerHeight;
    const paddingPantalla = 12;

    const espacioAbajo = viewportAlto - rect.bottom;
    const espacioArriba = rect.top - marginMinimoTop;

    let posEfectiva: "abajo" | "arriba" = "abajo";
    if (espacioAbajo < altoPop && espacioArriba >= altoPop) {
      posEfectiva = "arriba";
    } else {
      posEfectiva = "abajo";
    }
    setPosicionEfectiva(posEfectiva);

    let top: number;
    if (posEfectiva === "arriba") {
      top = rect.top - altoPop - 6;
    } else {
      top = rect.bottom + 6;
    }

    top = Math.max(marginMinimoTop, Math.min(top, viewportAlto - altoPop - 8));

    let left = rect.left;
    if (left + anchoPop > viewportAncho - paddingPantalla) {
      left = viewportAncho - anchoPop - paddingPantalla;
    }
    left = Math.max(paddingPantalla, left);

    setEstiloPopover({
      position: "fixed",
      top: `${top}px`,
      left: `${left}px`,
      zIndex: 99999,
    });
  }

  useEffect(() => {
    if (abierto) {
      recalcularPosicion();
      const manejarResize = () => recalcularPosicion();
      window.addEventListener("resize", manejarResize);
      window.addEventListener("scroll", manejarResize, true);
      return () => {
        window.removeEventListener("resize", manejarResize);
        window.removeEventListener("scroll", manejarResize, true);
      };
    }
  }, [abierto]);

  function alternarAbierto() {
    if (disabled) return;
    if (!abierto) {
      recalcularPosicion();
    }
    setAbierto(!abierto);
  }

  function seleccionar(h: string, m: string) {
    setHoraSel(h);
    setMinSel(m);
    onChange(`${h}:${m}`);
    setAbierto(false);
  }

  function seleccionarHoraActual() {
    const hoy = new Date();
    const h = String(hoy.getHours()).padStart(2, "0");
    const m = String(hoy.getMinutes()).padStart(2, "0");
    seleccionar(h, m);
  }

  function limpiar() {
    onChange(undefined);
    setAbierto(false);
  }

  return (
    <div ref={containerRef} className={`relative inline-block w-full ${className}`}>
      {label && (
        <label className="mb-1 block text-sm font-medium text-zinc-700">
          {label}
          {requerido && <span className="text-peligro"> *</span>}
        </label>
      )}

      <div
        onClick={alternarAbierto}
        className={`flex min-h-tactil w-full cursor-pointer items-center justify-between gap-1 rounded-lg border bg-white px-2.5 py-2 text-xs sm:text-sm shadow-sm transition-colors ${
          disabled
            ? "cursor-not-allowed bg-zinc-100 text-zinc-400"
            : "border-zinc-300 hover:border-zinc-400 focus:border-zinc-500"
        } ${abierto ? "border-zinc-500 ring-1 ring-zinc-500" : ""}`}
      >
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <Clock style={{ color: "var(--color-secundario)" }} className="h-4 w-4 shrink-0" aria-hidden />
          <span className={`truncate min-w-0 ${value ? "text-zinc-900 font-medium" : "text-zinc-400"}`}>
            {value || placeholder}
          </span>
        </div>
        {value && !disabled && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              limpiar();
            }}
            className="shrink-0 rounded p-0.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
            title="Limpiar hora"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {abierto && createPortal(
        <div
          ref={popoverRef}
          style={estiloPopover}
          className="animate-in fade-in zoom-in-95 w-60 max-w-[calc(100vw-24px)] rounded-xl border border-zinc-200 bg-white p-3 shadow-2xl duration-100"
        >
          <div className="flex gap-2">
            <div className="flex-1">
              <span className="mb-1 block text-center text-xs font-semibold text-zinc-500">Hora</span>
              <div className="max-h-40 overflow-y-auto rounded-lg border border-zinc-100 p-1 divide-y divide-zinc-50">
                {HORAS.map((h) => (
                  <button
                    key={h}
                    type="button"
                    onClick={() => seleccionar(h, minSel)}
                    className={`w-full py-1 text-center text-xs rounded transition-colors ${
                      h === horaSel ? "bg-zinc-900 text-white font-semibold" : "text-zinc-700 hover:bg-zinc-100"
                    }`}
                  >
                    {h}:00
                  </button>
                ))}
              </div>
            </div>

            <div className="w-24">
              <span className="mb-1 block text-center text-xs font-semibold text-zinc-500">Minutos</span>
              <div className="flex flex-col gap-1">
                {MINUTOS_SUGERIDOS.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => seleccionar(horaSel, m)}
                    className={`w-full py-1.5 text-center text-xs rounded-lg border transition-colors ${
                      m === minSel
                        ? "bg-zinc-900 text-white border-zinc-900 font-semibold"
                        : "border-zinc-200 text-zinc-700 hover:bg-zinc-100"
                    }`}
                  >
                    :{m}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between border-t border-zinc-100 pt-2 text-xs font-medium">
            <button
              type="button"
              onClick={seleccionarHoraActual}
              className="text-zinc-700 hover:text-zinc-900 hover:underline"
            >
              Ahora
            </button>
            {value && (
              <button
                type="button"
                onClick={limpiar}
                className="text-peligro hover:underline"
              >
                Limpiar
              </button>
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}

