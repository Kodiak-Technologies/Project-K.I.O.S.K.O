// Selector de categoría con campo inline para crear una nueva al vuelo.
// Reutilizado en GestionProductos.
import { useState } from "react";
import { Plus } from "lucide-react";
import { Button, Input, Select } from "../../../shared/components/ui";
import { useCategorias } from "../hooks/useCategorias";
import type { Categoria } from "../types";

interface Props {
  value: number | null | undefined;
  onChange: (id: number | null) => void;
  error?: string | null;
}

export function SelectorCategoria({ value, onChange, error }: Props) {
  const { categorias, crear } = useCategorias();
  const [nueva, setNueva] = useState("");
  const [creando, setCreando] = useState(false);
  const [errorCrear, setErrorCrear] = useState<string | null>(null);

  async function manejarAgregar() {
    if (!nueva.trim()) return;
    setCreando(true);
    setErrorCrear(null);
    try {
      const creada: Categoria = await crear({ nombre: nueva.trim() });
      onChange(creada.id);
      setNueva("");
    } catch (e) {
      setErrorCrear(e instanceof Error ? e.message : "No se pudo crear la categoría.");
    } finally {
      setCreando(false);
    }
  }

  return (
    <div className="space-y-2">
      <Select
        label="Categoría"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        error={error}
      >
        <option value="">Sin categoría</option>
        {categorias.map((c) => (
          <option key={c.id} value={c.id}>
            {c.nombre}
          </option>
        ))}
      </Select>
      <div className="flex items-end gap-2">
        <Input
          label="Nueva categoría"
          placeholder="ej. Abarrotes"
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
        />
        <Button
          type="button"
          variante="secundario"
          onClick={() => void manejarAgregar()}
          cargando={creando}
          icono={<Plus className="h-4 w-4" aria-hidden />}
        >
          Agregar
        </Button>
      </div>
      {errorCrear && <p className="text-xs text-red-700">{errorCrear}</p>}
    </div>
  );
}
