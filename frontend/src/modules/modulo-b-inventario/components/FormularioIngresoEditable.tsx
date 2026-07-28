// sdd/modulo-b-aprobaciones-detalle-editar: editable form for SolicitudIngreso
// (cabecera + lineas). Mirror del patrón de FormularioProveedor.
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Alert, Button, Input } from "../../../shared/components/ui";
import { SelectorProducto } from "./SelectorProducto";
import type { SolicitudIngreso, SolicitudIngresoUpdateBody } from "../types";

interface Props {
  inicial: SolicitudIngreso;
  onSubmit: (body: SolicitudIngresoUpdateBody) => Promise<void> | void;
  onCancel: () => void;
  /** Si ya está enviando (spinner). */
  procesando?: boolean;
  /** Error a mostrar (ej. response 422). */
  error?: string | null;
}

interface LineaLocal {
  producto_id: number | null;
  cantidad: number;
  precio_unitario: number;
}

export function FormularioIngresoEditable({
  inicial,
  onSubmit,
  onCancel,
  procesando,
  error,
}: Props) {
  const [motivo, setMotivo] = useState(inicial.motivo ?? "");
  const [lineas, setLineas] = useState<LineaLocal[]>(
    inicial.lineas.map((l) => ({
      producto_id: l.producto_id,
      cantidad: l.cantidad,
      precio_unitario: l.precio_compra_unitario,
    })),
  );

  // Resync si cambia la solicitud inicial (p. ej. tras recargar)
  useEffect(() => {
    setMotivo(inicial.motivo ?? "");
    setLineas(
      inicial.lineas.map((l) => ({
        producto_id: l.producto_id,
        cantidad: l.cantidad,
        precio_unitario: l.precio_compra_unitario,
      })),
    );
  }, [inicial]);

  const cantidadTotal = lineas.reduce((acc, l) => acc + (l.cantidad || 0), 0);
  const montoTotal = lineas.reduce(
    (acc, l) => acc + (l.cantidad || 0) * (l.precio_unitario || 0),
    0,
  );

  function agregarLinea() {
    setLineas((prev) => [...prev, { producto_id: null, cantidad: 1, precio_unitario: 0 }]);
  }
  function quitarLinea(idx: number) {
    setLineas((prev) => prev.filter((_, i) => i !== idx));
  }
  function actualizarLinea(idx: number, patch: Partial<LineaLocal>) {
    setLineas((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  }

  function validar(): string | null {
    for (let i = 0; i < lineas.length; i++) {
      const l = lineas[i];
      if (!l.producto_id) return `Línea ${i + 1}: selecciona un producto.`;
      if (l.cantidad <= 0) return `Línea ${i + 1}: la cantidad debe ser > 0.`;
      if (l.precio_unitario < 0) return `Línea ${i + 1}: el precio no puede ser negativo.`;
    }
    return null;
  }

  async function manejarSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validar();
    if (err) return;
    const body: SolicitudIngresoUpdateBody = {
      motivo: motivo.trim() === "" ? null : motivo.trim(),
      lineas: lineas.map((l) => ({
        producto_id: l.producto_id as number,
        cantidad: l.cantidad,
        precio_unitario: l.precio_unitario,
      })),
    };
    await onSubmit(body);
  }

  return (
    <form onSubmit={manejarSubmit} className="space-y-4">
      <Input
        label="Motivo (opcional)"
        placeholder="ej. corrección de proveedor"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        maxLength={500}
      />

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-zinc-800">Líneas</h4>
          <Button type="button" compacto variante="secundario" onClick={agregarLinea}>
            <Plus className="mr-1 h-4 w-4" /> Agregar línea
          </Button>
        </div>
        <div className="overflow-hidden rounded-lg border border-zinc-200">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-xs uppercase text-zinc-500">
              <tr>
                <th className="px-3 py-2 text-left">Producto</th>
                <th className="px-3 py-2 text-right">Cantidad</th>
                <th className="px-3 py-2 text-right">Precio unit.</th>
                <th className="px-3 py-2 text-right">Subtotal</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {lineas.map((l, i) => (
                <tr key={i} className="border-t border-zinc-100">
                  <td className="px-3 py-2">
                    <SelectorProducto
                      value={l.producto_id}
                      onChange={(id) => actualizarLinea(i, { producto_id: id })}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      min={1}
                      className="w-20 rounded border border-zinc-200 px-2 py-1 text-right tabular-nums"
                      value={l.cantidad}
                      onChange={(e) =>
                        actualizarLinea(i, { cantidad: Math.max(1, Number(e.target.value) || 1) })
                      }
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      className="w-24 rounded border border-zinc-200 px-2 py-1 text-right tabular-nums"
                      value={l.precio_unitario}
                      onChange={(e) =>
                        actualizarLinea(i, {
                          precio_unitario: Math.max(0, Number(e.target.value) || 0),
                        })
                      }
                    />
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {(l.cantidad * l.precio_unitario).toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => quitarLinea(i)}
                      aria-label="Quitar línea"
                      className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-peligro"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {lineas.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-center text-xs text-zinc-500">
                    Sin líneas. Agregá al menos una para guardar.
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot className="bg-zinc-50">
              <tr>
                <td className="px-3 py-2 text-right text-xs text-zinc-500" colSpan={1}>
                  Totales
                </td>
                <td className="px-3 py-2 text-right text-sm font-medium tabular-nums">
                  {cantidadTotal}
                </td>
                <td className="px-3 py-2" />
                <td className="px-3 py-2 text-right text-sm font-medium tabular-nums">
                  S/ {montoTotal.toFixed(2)}
                </td>
                <td className="px-3 py-2" />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {error && <Alert tono="peligro">{error}</Alert>}

      <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
        <Button type="button" variante="secundario" onClick={onCancel} disabled={procesando}>
          Cancelar
        </Button>
        <Button type="submit" cargando={procesando} disabled={lineas.length === 0}>
          Guardar cambios
        </Button>
      </div>
    </form>
  );
}
