import { useEffect, useRef, useState } from "react";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";

export interface DatePickerProps {
  valor?: string;
  value?: string;
  alCambiar?: (fechaIso: string) => void;
  onChange?: (fechaIso: string) => void;
  deshabilitado?: boolean;
  disabled?: boolean;
  etiqueta?: string;
  label?: string;
  placeholder?: string;
  mostrarAnio?: boolean;
  requerido?: boolean;
  error?: string | null;
  className?: string;
  alineacion?: "izquierda" | "derecha";
  posicion?: "abajo" | "arriba" | "auto";
  "aria-label"?: string;
}

const MESES_ES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const MESES_CORTOS_ES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Dic",
];

const DIAS_ES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];

function isoAFechaLocal(iso: string): Date | null {
  if (!iso) return null;
  const partes = iso.split("-");
  if (partes.length !== 3) return null;
  const y = Number(partes[0]);
  const m = Number(partes[1]) - 1;
  const d = Number(partes[2]);
  if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
  return new Date(y, m, d);
}

function fechaLocalAIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dia}`;
}

export function DatePicker({
  valor,
  value,
  alCambiar,
  onChange,
  deshabilitado,
  disabled,
  etiqueta,
  label,
  placeholder,
  mostrarAnio = false,
  requerido = false,
  error,
  className = "",
  alineacion = "izquierda",
  posicion = "auto",
  "aria-label": ariaLabel,
}: DatePickerProps) {
  const valorFinal = valor ?? value;
  const alCambiarFinal = alCambiar ?? onChange;
  const deshabilitadoFinal = deshabilitado || disabled || false;
  const etiquetaFinal = etiqueta ?? label;
  const placeholderFinal = placeholder || "dd/mm/aaaa";

  const [abierto, setAbierto] = useState(false);
  const [posicionEfectiva, setPosicionEfectiva] = useState<"abajo" | "arriba">("abajo");
  const [estiloPopover, setEstiloPopover] = useState<React.CSSProperties>({});
  const containerRef = useRef<HTMLDivElement>(null);

  const fechaObjeto = valorFinal ? isoAFechaLocal(valorFinal) : null;
  const hoy = new Date();
  const hoyIso = fechaLocalAIso(hoy);

  const [mesVista, setMesVista] = useState<number>(() => (fechaObjeto ? fechaObjeto.getMonth() : hoy.getMonth()));
  const [anioVista, setAnioVista] = useState<number>(() => (fechaObjeto ? fechaObjeto.getFullYear() : hoy.getFullYear()));
  const [vista, setVista] = useState<"dias" | "meses" | "anios">("dias");
  const [rangoAnioInicio, setRangoAnioInicio] = useState<number>(() => Math.floor(anioVista / 12) * 12);

  useEffect(() => {
    if (fechaObjeto) {
      setMesVista(fechaObjeto.getMonth());
      setAnioVista(fechaObjeto.getFullYear());
    }
  }, [valorFinal]);

  useEffect(() => {
    function manejarClicAfuera(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", manejarClicAfuera);
    return () => document.removeEventListener("mousedown", manejarClicAfuera);
  }, []);

  function recalcularPosicion() {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const espacioAbajo = window.innerHeight - rect.bottom;
    const topBarAlto = 64; // Altura de la barra superior (TopBar)
    const espacioArribaReal = rect.top - topBarAlto;

    if (posicion === "arriba") {
      setPosicionEfectiva("arriba");
    } else if (posicion === "abajo") {
      setPosicionEfectiva("abajo");
    } else if (espacioAbajo < 380 && espacioArribaReal >= 320) {
      // Solo abrir hacia arriba si hay espacio de al menos 320px libre por debajo de la TopBar
      setPosicionEfectiva("arriba");
    } else {
      setPosicionEfectiva("abajo");
    }

    const anchoCalendario = 288; // w-72 = 288px
    const viewportAncho = window.innerWidth;
    const paddingPantalla = 12; // 12px de margen mínimo de pantalla

    const nuevoEstilo: React.CSSProperties = {};

    if (alineacion === "derecha") {
      const leftEsperado = rect.right - anchoCalendario;
      if (leftEsperado < paddingPantalla) {
        const offsetLeft = paddingPantalla - rect.left;
        nuevoEstilo.left = `${offsetLeft}px`;
        nuevoEstilo.right = "auto";
      } else {
        nuevoEstilo.right = "0px";
        nuevoEstilo.left = "auto";
      }
    } else {
      const rightEsperado = rect.left + anchoCalendario;
      if (rightEsperado > viewportAncho - paddingPantalla) {
        const overflow = rightEsperado - (viewportAncho - paddingPantalla);
        nuevoEstilo.left = `-${overflow}px`;
      } else if (rect.left < paddingPantalla) {
        const offset = paddingPantalla - rect.left;
        nuevoEstilo.left = `${offset}px`;
      } else {
        nuevoEstilo.left = "0px";
      }
    }

    setEstiloPopover(nuevoEstilo);
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
    if (deshabilitadoFinal) return;
    if (!abierto) {
      recalcularPosicion();
    }
    setAbierto(!abierto);
  }

  const textoBoton = fechaObjeto
    ? mostrarAnio
      ? `${String(fechaObjeto.getDate()).padStart(2, "0")}/${String(fechaObjeto.getMonth() + 1).padStart(2, "0")}/${fechaObjeto.getFullYear()}`
      : `${String(fechaObjeto.getDate()).padStart(2, "0")}/${String(fechaObjeto.getMonth() + 1).padStart(2, "0")}`
    : placeholderFinal;

  function mesAnterior() {
    if (mesVista === 0) {
      setMesVista(11);
      setAnioVista((a) => a - 1);
    } else {
      setMesVista((m) => m - 1);
    }
  }

  function mesSiguiente() {
    if (mesVista === 11) {
      setMesVista(0);
      setAnioVista((a) => a + 1);
    } else {
      setMesVista((m) => m + 1);
    }
  }

  function seleccionarDia(dia: number) {
    const nuevaFecha = new Date(anioVista, mesVista, dia);
    const isoStr = fechaLocalAIso(nuevaFecha);
    if (alCambiarFinal) alCambiarFinal(isoStr);
    setAbierto(false);
  }

  function seleccionarMes(mIdx: number) {
    setMesVista(mIdx);
    setVista("dias");
  }

  function seleccionarAnio(a: number) {
    setAnioVista(a);
    setVista("meses");
  }

  function seleccionarHoy() {
    const hoyObj = new Date();
    setMesVista(hoyObj.getMonth());
    setAnioVista(hoyObj.getFullYear());
    const isoStr = fechaLocalAIso(hoyObj);
    if (alCambiarFinal) alCambiarFinal(isoStr);
    setAbierto(false);
  }

  const primerDiaMes = new Date(anioVista, mesVista, 1);
  const diaSemanaInicio = (primerDiaMes.getDay() + 6) % 7;
  const diasEnMes = new Date(anioVista, mesVista + 1, 0).getDate();

  const celdas: { dia: number; esMesActual: boolean; fechaIso: string }[] = [];
  for (let i = 0; i < diaSemanaInicio; i++) {
    celdas.push({ dia: 0, esMesActual: false, fechaIso: "" });
  }
  for (let d = 1; d <= diasEnMes; d++) {
    const fIso = fechaLocalAIso(new Date(anioVista, mesVista, d));
    celdas.push({ dia: d, esMesActual: true, fechaIso: fIso });
  }

  const aniosRango = Array.from({ length: 12 }, (_, i) => rangoAnioInicio + i);

  return (
    <div ref={containerRef} className={`relative inline-block w-full ${className}`}>
      {etiquetaFinal && (
        <label className="mb-1 block text-sm font-medium text-zinc-700">
          {etiquetaFinal}
          {requerido && <span className="text-peligro"> *</span>}
        </label>
      )}

      <div
        tabIndex={deshabilitadoFinal ? -1 : 0}
        role="button"
        aria-label={ariaLabel || etiquetaFinal || "Seleccionar fecha"}
        aria-expanded={abierto}
        onClick={alternarAbierto}
        onKeyDown={(e) => {
          if (!deshabilitadoFinal && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            alternarAbierto();
          }
        }}
        title={fechaObjeto ? fechaLocalAIso(fechaObjeto) : undefined}
        className={`flex min-h-tactil w-full cursor-pointer items-center justify-between gap-2 rounded-lg border bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm transition-all ${
          deshabilitadoFinal
            ? "cursor-not-allowed border-zinc-200 bg-zinc-100 text-zinc-400"
            : error
            ? "border-peligro ring-1 ring-peligro"
            : "border-zinc-300 hover:border-zinc-400 focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
        } ${abierto ? "border-zinc-500 ring-1 ring-zinc-500" : ""}`}
      >
        <span className={`truncate ${!fechaObjeto ? "text-zinc-400" : "font-medium text-zinc-800"}`}>
          {textoBoton}
        </span>
        <CalendarIcon
          style={{ color: "var(--color-secundario)" }}
          className="h-4 w-4 shrink-0 transition-transform hover:scale-110"
        />
      </div>

      {abierto && !deshabilitadoFinal && (
        <div
          style={estiloPopover}
          className={`animate-in fade-in zoom-in-95 absolute z-[9999] w-72 max-w-[calc(100vw-24px)] rounded-xl border border-zinc-200 bg-white p-3.5 shadow-2xl duration-100 ${
            posicionEfectiva === "arriba" ? "bottom-full mb-1.5" : "top-full mt-1.5"
          }`}
        >
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              onClick={() => {
                if (vista === "dias") mesAnterior();
                else if (vista === "meses") setAnioVista((a) => a - 1);
                else setRangoAnioInicio((r) => r - 12);
              }}
              className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <div className="flex items-center gap-1 text-sm font-semibold text-zinc-900">
              {vista === "anios" ? (
                <span>
                  {rangoAnioInicio} - {rangoAnioInicio + 11}
                </span>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setVista((v) => (v === "meses" ? "dias" : "meses"))}
                    className="rounded px-1.5 py-0.5 font-semibold text-zinc-900 hover:bg-zinc-100"
                  >
                    {MESES_ES[mesVista]}
                  </button>
                  <button
                    type="button"
                    onClick={() => setVista((v) => (v === "anios" ? "dias" : "anios"))}
                    className="rounded px-1.5 py-0.5 font-semibold text-zinc-900 hover:bg-zinc-100"
                  >
                    {anioVista}
                  </button>
                </>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                if (vista === "dias") mesSiguiente();
                else if (vista === "meses") setAnioVista((a) => a + 1);
                else setRangoAnioInicio((r) => r + 12);
              }}
              className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {vista === "dias" && (
            <>
              <div className="mb-1.5 grid grid-cols-7 text-center text-xs font-medium text-zinc-400">
                {DIAS_ES.map((d) => (
                  <div key={d} className="py-1">
                    {d}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-7 gap-1 text-center text-xs">
                {celdas.map((c, idx) => {
                  if (!c.esMesActual) {
                    return (
                      <div key={idx} className="py-1.5 text-zinc-300">
                        {c.dia}
                      </div>
                    );
                  }
                  const esSeleccionado = c.fechaIso === valorFinal;
                  const esHoy = c.fechaIso === hoyIso;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => seleccionarDia(c.dia)}
                      className={`h-8 w-8 rounded-lg text-xs transition-all ${
                        esSeleccionado
                          ? "bg-zinc-900 font-semibold text-white shadow-sm"
                          : esHoy
                          ? "border border-zinc-400 font-bold text-zinc-900 hover:bg-zinc-100"
                          : "text-zinc-700 hover:bg-zinc-100"
                      }`}
                    >
                      {c.dia}
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {vista === "meses" && (
            <div className="grid grid-cols-3 gap-2 py-2">
              {MESES_CORTOS_ES.map((m, idx) => {
                const esMesSeleccionado = idx === mesVista;
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => seleccionarMes(idx)}
                    className={`rounded-lg py-2.5 text-xs font-medium transition-colors ${
                      esMesSeleccionado
                        ? "bg-zinc-900 font-semibold text-white"
                        : "text-zinc-700 hover:bg-zinc-100"
                    }`}
                  >
                    {m}
                  </button>
                );
              })}
            </div>
          )}

          {vista === "anios" && (
            <div className="grid grid-cols-3 gap-2 py-2">
              {aniosRango.map((a) => {
                const esAnioSeleccionado = a === anioVista;
                return (
                  <button
                    key={a}
                    type="button"
                    onClick={() => seleccionarAnio(a)}
                    className={`rounded-lg py-2.5 text-xs font-medium transition-colors ${
                      esAnioSeleccionado
                        ? "bg-zinc-900 font-semibold text-white"
                        : "text-zinc-700 hover:bg-zinc-100"
                    }`}
                  >
                    {a}
                  </button>
                );
              })}
            </div>
          )}

          <div className="mt-3 border-t border-zinc-100 pt-2.5 flex items-center justify-between">
            <button
              type="button"
              onClick={seleccionarHoy}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Hoy
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-1 text-xs text-peligro">{error}</p>}
    </div>
  );
}
