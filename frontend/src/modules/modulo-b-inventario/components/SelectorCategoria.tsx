// Selector de categoría para el alta de producto desde un ingreso.
//
// A diferencia de `SelectorProducto`, acá un `<select>` nativo alcanza: las
// categorías son decenas, no miles, y el listado viene entero en una llamada.
// La categoría es opcional (`productos.categoria_id` es nullable), así que el
// selector siempre ofrece la opción vacía.
import { useCategorias } from "../hooks/useCategorias";

interface Props {
  value: number | null;
  onChange: (id: number | null) => void;
  disabled?: boolean;
}

export function SelectorCategoria({ value, onChange, disabled }: Props) {
  const { categorias, cargando } = useCategorias();

  return (
    <select
      className="w-full rounded border border-zinc-200 px-2 py-1 text-sm text-zinc-900 disabled:bg-zinc-50"
      value={value ?? ""}
      disabled={disabled || cargando}
      aria-label="Categoría"
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
    >
      <option value="">{cargando ? "Cargando…" : "Sin categoría"}</option>
      {categorias
        .filter((c) => c.activo)
        .map((c) => (
          <option key={c.id} value={c.id}>
            {c.nombre}
          </option>
        ))}
    </select>
  );
}
