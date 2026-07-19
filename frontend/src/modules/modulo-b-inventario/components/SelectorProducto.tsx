// Selector de producto con búsqueda por código o nombre (debounce 300ms).
// Reutilizado en: IngresosMercaderia, Mermas, AprobacionMermas, MovimientosInventario.
import { useEffect, useState } from "react";
import { Loader2, Search, X } from "lucide-react";
import { Select } from "../../../shared/components/ui";
import { productosHttpAdapter } from "../services/productos.http-adapter";
import type { Producto } from "../types";

interface Props {
  /** Etiqueta visible. */
  label?: string;
  /** Valor controlado. `null` o `undefined` = nada seleccionado. */
  value: number | null | undefined;
  onChange: (id: number | null) => void;
  /** Si el producto es requerido (le agrega asterisco). */
  requerido?: boolean;
  /** Filtra solo productos activos. Default true. */
  soloActivos?: boolean;
  /** Deshabilita el selector. */
  disabled?: boolean;
  /** Mensaje de error a mostrar debajo. */
  error?: string | null;
}

const DEBOUNCE_MS = 300;

/**
 * Selector de producto para los formularios del módulo.
 *
 * Por qué un selector custom y no un `<select>` con 2000 productos:
 *   el catálogo puede tener miles de SKUs y el `<select>` nativo se vuelve
 *   injusable en mobile. Acá se busca por nombre o código, con debounce,
 *   y se muestra el nombre del producto seleccionado.
 */
export function SelectorProducto({
  label = "Producto",
  value,
  onChange,
  requerido,
  soloActivos = true,
  disabled,
  error,
}: Props) {
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState<Producto[]>([]);
  const [cargando, setCargando] = useState(false);
  const [productoSeleccionado, setProductoSeleccionado] = useState<Producto | null>(null);

  // Si nos pasan un `value` distinto del que ya tenemos en memoria, lo cargamos
  // para mostrar su nombre (caso "Reponer" desde el catálogo).
  useEffect(() => {
    if (value && (!productoSeleccionado || productoSeleccionado.id !== value)) {
      productosHttpAdapter
        .obtener(value)
        .then((p) => setProductoSeleccionado(p))
        .catch(() => setProductoSeleccionado(null));
    } else if (!value) {
      setProductoSeleccionado(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // Búsqueda con debounce.
  useEffect(() => {
    if (!busqueda.trim()) {
      setResultados([]);
      return;
    }
    const handle = window.setTimeout(async () => {
      setCargando(true);
      try {
        const data = await productosHttpAdapter.buscar(undefined, busqueda.trim());
        const lista = Array.isArray(data) ? data : [data];
        setResultados(soloActivos ? lista.filter((p) => p.activo) : lista);
      } catch {
        setResultados([]);
      } finally {
        setCargando(false);
      }
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [busqueda, soloActivos]);

  function elegir(p: Producto) {
    setProductoSeleccionado(p);
    onChange(p.id);
    setBusqueda("");
    setResultados([]);
  }

  function limpiar() {
    setProductoSeleccionado(null);
    onChange(null);
    setBusqueda("");
    setResultados([]);
  }

  // Si ya hay un producto elegido, mostramos su nombre y un botón para limpiar.
  if (productoSeleccionado) {
    return (
      <div>
        <span className="mb-1 block text-sm font-medium text-zinc-700">
          {label}
          {requerido && <span className="text-peligro"> *</span>}
        </span>
        <div className="flex items-center gap-2 rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm">
          <span className="flex-1 truncate">
            <span className="font-mono text-xs text-zinc-500">{productoSeleccionado.codigo}</span>{" "}
            <span className="text-zinc-800">{productoSeleccionado.nombre}</span>
            {productoSeleccionado.stock !== undefined && (
              <span className="ml-2 text-xs text-zinc-500">(stock: {productoSeleccionado.stock})</span>
            )}
          </span>
          <button
            type="button"
            onClick={limpiar}
            disabled={disabled}
            aria-label="Cambiar producto"
            className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 disabled:opacity-50"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
      </div>
    );
  }

  return (
    <div className="relative">
      <span className="mb-1 block text-sm font-medium text-zinc-700">
        {label}
        {requerido && <span className="text-peligro"> *</span>}
      </span>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" aria-hidden />
        <input
          type="text"
          disabled={disabled}
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar por nombre o código…"
          className="w-full min-h-tactil rounded-lg border border-zinc-300 bg-white pl-9 pr-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-500 disabled:bg-zinc-50"
        />
        {cargando && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-zinc-400" aria-hidden />
        )}
      </div>
      {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
      {busqueda.trim() && !cargando && (
        <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-zinc-200 bg-white shadow-lg">
          {resultados.length === 0 ? (
            <li className="px-3 py-2 text-sm text-zinc-500">Sin resultados.</li>
          ) : (
            resultados.slice(0, 20).map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => elegir(p)}
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-zinc-50"
                >
                  <span className="font-mono text-xs text-zinc-500">{p.codigo}</span>{" "}
                  <span className="text-zinc-800">{p.nombre}</span>
                  {p.stock !== undefined && (
                    <span className="ml-2 text-xs text-zinc-400">stock: {p.stock}</span>
                  )}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
