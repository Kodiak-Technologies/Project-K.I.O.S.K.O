// Una línea del formulario de Ingresos de mercadería: producto + cantidad + precio.
// Reutilizado en IngresosMercaderia (N líneas dinámicas).
import { Trash2 } from "lucide-react";
import { Input } from "../../../shared/components/ui";
import { SelectorProducto } from "./SelectorProducto";

export interface LineaIngreso {
  /** `null` o `undefined` = aún no elegida. */
  producto_id: number | null;
  cantidad: number;
  precio_compra_unitario: number;
}

interface Props {
  linea: LineaIngreso;
  /** Errores de validación de la línea. */
  errores?: { producto_id?: string; cantidad?: string; precio_compra_unitario?: string };
  /** Si es la única línea, no se puede eliminar. */
  esUnica: boolean;
  onChange: (linea: LineaIngreso) => void;
  onEliminar: () => void;
}

export function FormularioLineaIngreso({
  linea,
  errores,
  esUnica,
  onChange,
  onEliminar,
}: Props) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Línea</span>
        {!esUnica && (
          <button
            type="button"
            onClick={onEliminar}
            aria-label="Eliminar línea"
            className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-peligro"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_6rem] lg:grid-cols-[1fr_6rem_9rem]">
        {/* Búsqueda contra el servidor: el catálogo puede tener miles de SKUs
            y traerlo entero rompía la pantalla al pasar el tope de la API. */}
        <SelectorProducto
          label="Producto"
          requerido
          value={linea.producto_id}
          onChange={(id) => onChange({ ...linea, producto_id: id })}
          error={errores?.producto_id}
        />
        <Input
          label="Cantidad"
          type="number"
          min={1}
          requerido
          value={linea.cantidad || ""}
          onChange={(e) => onChange({ ...linea, cantidad: Number(e.target.value) })}
          error={errores?.cantidad}
        />
        <Input
          label="Precio compra (S/)"
          type="number"
          step="0.01"
          min={0}
          value={linea.precio_compra_unitario || ""}
          onChange={(e) =>
            onChange({ ...linea, precio_compra_unitario: Number(e.target.value) })
          }
          error={errores?.precio_compra_unitario}
        />
      </div>
    </div>
  );
}
