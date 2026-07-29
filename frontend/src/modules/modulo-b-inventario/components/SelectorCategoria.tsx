// Selector de categoría para el alta de producto desde un ingreso.
import { Select } from "../../../shared/components/ui";
import { useCategorias } from "../hooks/useCategorias";

interface Props {
  value: number | null;
  onChange: (id: number | null) => void;
  disabled?: boolean;
}

export function SelectorCategoria({ value, onChange, disabled }: Props) {
  const { categorias, cargando } = useCategorias();

  return (
    <Select
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
    </Select>
  );
}
